"""SoundFlow Studio v0.5 local server. Start with `uvicorn app:app --host 127.0.0.1 --port 8765`."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import json
import os
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from typing import Literal

from fastapi import Form
from pydantic import BaseModel, Field

from core import (MixClip, Segment, group_words, merge_segments, probe_media, render_audio,
                  render_mix, render_video)
from elevenlabs_client import create_music, transcribe, create_text_music, create_sound_effect

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DUCKING_DATA_DIR", str(ROOT / "runtime"))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD = 100 * 1024 * 1024
ALLOWED_VIDEO = {".mp4", ".mov", ".webm", ".mkv"}
ALLOWED_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
app = FastAPI(title="SoundFlow Studio v0.5", docs_url="/api/docs", redoc_url=None)


class MusicOptions(BaseModel):
    description: str = Field(default="", max_length=4100)
    reference_audio: bool = False


class TimelineOptions(BaseModel):
    gap: float = Field(default=1.0, ge=0, le=5)


class MixOptions(BaseModel):
    gap: float = Field(default=1.0, ge=0, le=5)
    reduction_db: float = Field(default=16, ge=0, le=36)
    normal_music_db: float = Field(default=-12, ge=-30, le=0)
    pre: float = Field(default=.15, ge=0, le=1)
    post: float = Field(default=.25, ge=0, le=2)
    attack: float = Field(default=.15, ge=0, le=2)
    release: float = Field(default=.55, ge=0, le=3)
    manual_segments: list[Segment] | None = None


def job_dir(job: str) -> Path:
    if len(job) != 32 or any(c not in "0123456789abcdef" for c in job):
        raise HTTPException(404, "Unknown job")
    folder = DATA / job
    if not folder.is_dir():
        raise HTTPException(404, "Job not found")
    return folder


def details(job: str, folder: Path) -> dict:
    meta = json.loads((folder / "meta.json").read_text())
    return {"job_id": job, **meta, "has_music": (folder / meta.get("music_name", "music.mp3")).exists(),
            "has_transcript": (folder / "words.json").exists(),
            "has_rendered": (folder / "output.mp4").exists(),
            "has_rendered_audio": (folder / "ducked_bgm.wav").exists()}


def store_upload(upload: UploadFile, target: Path) -> None:
    written = 0
    try:
        with target.open("wb") as f:
            while buf := upload.file.read(1024 * 1024):
                written += len(buf)
                if written > MAX_UPLOAD:
                    raise HTTPException(413, "Demo upload limit: 100 MB")
                f.write(buf)
        if written == 0:
            raise HTTPException(400, "Empty upload")
    except Exception:
        target.unlink(missing_ok=True)
        raise


def video_file(folder: Path) -> Path:
    meta = json.loads((folder / "meta.json").read_text())
    return folder / meta["video_name"]


def require_music(folder: Path) -> Path:
    # files with original extension are renamed to music.mp3 only when actually MP3;
    # when user uploads non-MP3, preserve extension in metadata.
    meta = json.loads((folder / "meta.json").read_text())
    music = folder / meta.get("music_name", "music.mp3")
    if not music.exists():
        raise HTTPException(400, "Please generate or upload music first")
    return music


def load_segments(folder: Path, duration: float, gap: float, manual: list[Segment] | None = None) -> list[Segment]:
    if manual is not None:
        if len(manual) > 1000:
            raise HTTPException(400, "Too many speech segments")
        for s in manual:
            if not (0 <= s.start < s.end <= duration + 0.01):
                raise HTTPException(400, "Invalid manual segment range")
        return merge_segments([Segment(s.start, min(s.end, duration)) for s in manual])
    words = folder / "words.json"
    if words.is_file():
        data = json.loads(words.read_text())
        return group_words(data.get("words", []), gap=gap, duration=duration)
    return []


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html", media_type="text/html")


@app.get("/api/health")
def health():
    return {"ffmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
            "elevenlabs_configured": bool(os.environ.get("ELEVENLABS_API_KEY", "").strip()),
            "mode": "local-demo"}


@app.post("/api/video")
def upload_video(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_VIDEO:
        raise HTTPException(400, "Expected MP4, MOV, WebM or MKV")
    job = uuid4().hex
    folder = DATA / job
    folder.mkdir(parents=True)
    filename = "video" + ext
    target = folder / filename
    try:
        store_upload(file, target)
        info = probe_media(target)
        if not info["has_video"] or info["duration"] > 600:
            raise HTTPException(400, "Video stream is required and duration cannot exceed 600s")
        (folder / "meta.json").write_text(json.dumps({"video_name": filename, **info}, ensure_ascii=False))
        return details(job, folder)
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/sample")
def sample():
    job = uuid4().hex
    folder = DATA / job
    folder.mkdir(parents=True)
    shutil.copy2(ROOT / "samples" / "sample_video.mp4", folder / "video.mp4")
    shutil.copy2(ROOT / "samples" / "sample_music.mp3", folder / "music.mp3")
    shutil.copy2(ROOT / "samples" / "sample_words.json", folder / "words.json")
    info = probe_media(folder / "video.mp4")
    (folder / "meta.json").write_text(json.dumps({"video_name": "video.mp4", "music_name": "music.mp3",
                                                   "sample": True, **info}, ensure_ascii=False))
    music = register_asset(folder, ROOT / "samples" / "sample_music.mp3", "music", "示例 BGM", "sample")
    sfx = register_asset(folder, ROOT / "samples" / "sample_sfx_whoosh.mp3", "sfx", "转场 Whoosh（示例）", "sample")
    starter = default_timeline(info["duration"], "产品视频 · 配乐示例")
    starter["clips"] = [
        {"id": "clip_music_1", "track": "music1", "asset": music["id"], "start": 0, "offset": 0,
         "length": round(min(info["duration"], music["duration"]), 3), "gain_db": 0, "fade_in": .8, "fade_out": 1.5},
        {"id": "clip_sfx_1", "track": "sfx1", "asset": sfx["id"], "start": 8.1, "offset": 0,
         "length": round(sfx["duration"], 3), "gain_db": -4, "fade_in": 0, "fade_out": .2},
    ]
    (folder / "timeline.json").write_text(json.dumps(starter, ensure_ascii=False))
    return details(job, folder)


@app.post("/api/music/{job}")
def music_generate(job: str, opt: MusicOptions):
    folder = job_dir(job)
    try:
        output = folder / "music.mp3"
        pending = folder / "music.pending.mp3"
        try:
            # Keep existing music until a complete, valid paid API result is received.
            create_music(video_file(folder), pending, description=opt.description,
                         reference_audio=opt.reference_audio)
            info = probe_media(pending)
            if not info["has_audio"]:
                raise ValueError("Generated music has no audio stream")
            pending.replace(output)
        finally:
            pending.unlink(missing_ok=True)
        meta = json.loads((folder / "meta.json").read_text())
        meta["music_name"] = "music.mp3"
        (folder / "meta.json").write_text(json.dumps(meta))
        return {"ok": True, "music_seconds": round(info["duration"], 2), "source": "elevenlabs"}
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc


@app.post("/api/music-upload/{job}")
def music_upload(job: str, file: UploadFile = File(...)):
    folder = job_dir(job)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AUDIO:
        raise HTTPException(400, "Expected MP3/WAV/M4A/AAC/FLAC/OGG")
    target = folder / ("music" + ext)
    try:
        store_upload(file, target)
        info = probe_media(target)
        if not info["has_audio"]:
            raise ValueError("No audio stream")
        meta = json.loads((folder / "meta.json").read_text())
        previous = folder / meta.get("music_name", "music.mp3")
        if previous != target:
            previous.unlink(missing_ok=True)
        meta["music_name"] = target.name
        (folder / "meta.json").write_text(json.dumps(meta))
        return {"ok": True, "music_seconds": round(info["duration"], 2), "source": "upload"}
    except Exception as exc:
        target.unlink(missing_ok=True)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/transcribe/{job}")
def speech_recognition(job: str):
    folder = job_dir(job)
    meta = json.loads((folder / "meta.json").read_text())
    if not meta["has_audio"]:
        raise HTTPException(400, "Video has no original audio: use manual segments or music-only mode")
    try:
        payload = transcribe(video_file(folder))
        (folder / "words.json").write_text(json.dumps(payload, ensure_ascii=False))
        return {"ok": True, "text": payload.get("text", ""), "word_count": len(payload.get("words", []))}
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/timeline/{job}")
def timeline(job: str, gap: float = 1.0):
    folder = job_dir(job)
    meta = json.loads((folder / "meta.json").read_text())
    try:
        windows = load_segments(folder, meta["duration"], gap)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    data = json.loads((folder / "words.json").read_text()) if (folder / "words.json").exists() else {}
    return {"segments": [s.as_dict() for s in windows], "text": data.get("text", ""),
            "words": data.get("words", []), "duration": meta["duration"]}


@app.post("/api/render/{job}")
def mix(job: str, opt: MixOptions):
    folder = job_dir(job)
    try:
        meta = json.loads((folder / "meta.json").read_text())
        ranges = load_segments(folder, meta["duration"], opt.gap, opt.manual_segments)
        result = render_video(video_file(folder), require_music(folder), folder / "output.mp4", ranges,
                              reduction_db=opt.reduction_db, normal_music_db=opt.normal_music_db,
                              pre=opt.pre, post=opt.post, attack=opt.attack, release=opt.release)
        result["speech_segments"] = [s.as_dict() for s in ranges]
        return result
    except HTTPException:
        raise
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/file/{job}/{kind}")
def read_file(job: str, kind: str):
    folder = job_dir(job)
    if kind == "video":
        path = video_file(folder)
    elif kind == "music":
        path = require_music(folder)
    elif kind == "result":
        path = folder / "output.mp4"
    elif kind == "audio":
        path = folder / "ducked_bgm.wav"
    else:
        raise HTTPException(404, "Unknown file type")
    if not path.exists():
        raise HTTPException(404, "File not ready")
    return FileResponse(path, filename=path.name if kind in ("result", "audio") else None)


class ProjectOptions(BaseModel):
    name: str = Field(default="未命名项目", min_length=1, max_length=100)
    mix: MixOptions


@app.post("/api/render-audio/{job}")
def render_track(job: str, opt: MixOptions):
    folder = job_dir(job)
    try:
        meta = json.loads((folder / "meta.json").read_text())
        ranges = load_segments(folder, meta["duration"], opt.gap, opt.manual_segments)
        return render_audio(require_music(folder), folder / "ducked_bgm.wav",
                            duration=meta["duration"], segments=ranges,
                            reduction_db=opt.reduction_db, normal_music_db=opt.normal_music_db,
                            pre=opt.pre, post=opt.post, attack=opt.attack, release=opt.release)
    except HTTPException:
        raise
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/project/{job}")
def save_project(job: str, opt: ProjectOptions):
    folder = job_dir(job)
    (folder / "project.json").write_text(opt.model_dump_json(indent=2))
    return {"ok": True, "job_id": job}


@app.get("/api/project/{job}")
def read_project(job: str):
    folder = job_dir(job)
    path = folder / "project.json"
    if not path.is_file():
        raise HTTPException(404, "No saved project")
    return json.loads(path.read_text())


@app.get("/api/projects")
def list_projects():
    projects = []
    for folder in sorted((p for p in DATA.iterdir() if p.is_dir()),
                         key=lambda p: p.stat().st_mtime, reverse=True):
        if len(projects) >= 30:
            break
        if folder.name == "assets" or not (folder / "meta.json").is_file():
            continue
        project_path = folder / "project.json"
        try:
            item = details(folder.name, folder)
            timeline_path = folder / "timeline.json"
            if timeline_path.is_file():
                tl = json.loads(timeline_path.read_text())
                item["name"] = tl.get("name") or "未命名项目"
                item["clip_count"] = len(tl.get("clips", []))
                item["ducking_enabled"] = bool(tl.get("ducking", {}).get("enabled"))
            else:
                item["name"] = (json.loads(project_path.read_text()).get("name")
                                if project_path.is_file() else "未命名项目")
                item["clip_count"] = 0
                item["ducking_enabled"] = False
            item["asset_count"] = len(list_assets(folder))
            item["updated_at"] = int(folder.stat().st_mtime)
            projects.append(item)
        except (ValueError, KeyError, OSError):
            continue
    return {"projects": projects}


# Standalone audio creative routes. These do not require a video or a ducking job.
class TextMusicOptions(BaseModel):
    prompt: str = Field(min_length=3, max_length=4100)
    duration_seconds: int = Field(default=30, ge=3, le=600)
    instrumental: bool = True


class SfxOptions(BaseModel):
    prompt: str = Field(min_length=3, max_length=3000)
    duration_seconds: float = Field(default=5, ge=.5, le=30)
    loop: bool = False


def _make_asset_dir() -> tuple[str, Path]:
    asset_id = uuid4().hex
    folder = DATA / 'assets' / asset_id
    folder.mkdir(parents=True, exist_ok=False)
    return asset_id, folder


def _asset_dir(asset_id: str) -> Path:
    if len(asset_id) != 32 or any(c not in '0123456789abcdef' for c in asset_id):
        raise HTTPException(404, 'Unknown asset')
    folder = DATA / 'assets' / asset_id
    if not folder.is_dir():
        raise HTTPException(404, 'Asset not found')
    return folder


@app.post('/api/create/music')
def generate_standalone_music(opt: TextMusicOptions):
    asset_id, folder = _make_asset_dir()
    try:
        audio = folder / 'music.mp3'
        create_text_music(opt.prompt.strip(), audio,
                          duration_seconds=opt.duration_seconds, instrumental=opt.instrumental)
        info = probe_media(audio)
        if not info['has_audio']:
            raise ValueError('No audio stream in generated music')
        return {'id': asset_id, 'kind': 'music', 'duration': info['duration'],
                'url': f'/api/assets/{asset_id}', 'download_url': f'/api/assets/{asset_id}?download=true'}
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(502, str(exc)) from exc


@app.post('/api/create/sfx')
def generate_standalone_sfx(opt: SfxOptions):
    asset_id, folder = _make_asset_dir()
    try:
        audio = folder / 'sfx.mp3'
        create_sound_effect(opt.prompt.strip(), audio,
                            duration_seconds=opt.duration_seconds, loop=opt.loop)
        info = probe_media(audio)
        if not info['has_audio']:
            raise ValueError('No audio stream in generated sound effect')
        return {'id': asset_id, 'kind': 'sfx', 'duration': info['duration'],
                'url': f'/api/assets/{asset_id}', 'download_url': f'/api/assets/{asset_id}?download=true'}
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(502, str(exc)) from exc


@app.get('/api/assets/{asset_id}')
def read_generated_asset(asset_id: str, download: bool = False):
    folder = _asset_dir(asset_id)
    audio = folder / 'music.mp3'
    if not audio.is_file():
        audio = folder / 'sfx.mp3'
    if not audio.is_file():
        raise HTTPException(404, 'Asset not ready')
    return FileResponse(audio, filename=audio.name if download else None,
                        media_type='audio/mpeg')


# ---------------------------------------------------------------------------
# v0.5 editor API: one project = one video + an asset library + a multi-track timeline.
# Ducking is a user-triggered action: POST /speech runs recognition (cached),
# and the timeline's `ducking.enabled` flag decides whether music is lowered.
# ---------------------------------------------------------------------------
ID_CHARS = set("0123456789abcdefghijklmnopqrstuvwxyz_-")


def _assets_path(folder: Path) -> Path:
    return folder / "assets.json"


def list_assets(folder: Path) -> list[dict]:
    path = _assets_path(folder)
    return json.loads(path.read_text()) if path.is_file() else []


def public_asset(job: str, asset: dict) -> dict:
    return {k: v for k, v in asset.items() if k != "file"} | {"url": f"/api/projects/{job}/assets/{asset['id']}"}


def register_asset(folder: Path, source: Path | None, kind: str, name: str, origin: str,
                   *, prompt: str = "", move: bool = False, ext: str | None = None) -> dict:
    """Copy/move an audio file into the project library and record its metadata."""
    asset_id = uuid4().hex
    library = folder / "assets"
    library.mkdir(exist_ok=True)
    target = library / f"{asset_id}{ext or (source.suffix.lower() if source else '.mp3')}"
    if source is not None:
        (shutil.move if move else shutil.copy2)(source, target)
    info = probe_media(target)
    if not info["has_audio"]:
        target.unlink(missing_ok=True)
        raise ValueError("Asset has no audio stream")
    item = {"id": asset_id, "kind": kind, "name": name[:80], "origin": origin, "prompt": prompt[:400],
            "duration": round(info["duration"], 3), "file": target.name}
    items = list_assets(folder)
    items.append(item)
    _assets_path(folder).write_text(json.dumps(items, ensure_ascii=False, indent=1))
    return item


def asset_file(folder: Path, asset_id: str) -> tuple[dict, Path]:
    for item in list_assets(folder):
        if item["id"] == asset_id:
            return item, folder / "assets" / item["file"]
    raise HTTPException(404, "Asset not found")


def default_timeline(duration: float, name: str = "未命名项目") -> dict:
    return {"name": name, "duration": round(duration, 3),
            "tracks": [{"id": "video", "kind": "video", "name": "原视频对白", "volume_db": 0, "mute": False, "duck": False},
                       {"id": "music1", "kind": "music", "name": "背景音乐", "volume_db": 0, "mute": False, "duck": True},
                       {"id": "sfx1", "kind": "sfx", "name": "音效 1", "volume_db": 0, "mute": False, "duck": False},
                       {"id": "sfx2", "kind": "sfx", "name": "音效 2", "volume_db": 0, "mute": False, "duck": False}],
            "clips": [],
            "ducking": {"enabled": False, "reduction_db": 16, "normal_db": 0, "gap": 1.0, "pre": .15,
                        "post": .25, "attack": .15, "release": .55, "segments": [], "edited": False}}


class TrackModel(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    kind: Literal["video", "music", "sfx"]
    name: str = Field(default="", max_length=60)
    volume_db: float = Field(default=0, ge=-60, le=12)
    mute: bool = False
    duck: bool = False


class ClipModel(BaseModel):
    id: str = Field(min_length=1, max_length=60)
    track: str = Field(min_length=1, max_length=40)
    asset: str = Field(min_length=32, max_length=32)
    start: float = Field(ge=0, le=600)
    offset: float = Field(default=0, ge=0, le=600)
    length: float = Field(gt=0, le=600)
    gain_db: float = Field(default=0, ge=-60, le=12)
    fade_in: float = Field(default=0, ge=0, le=10)
    fade_out: float = Field(default=0, ge=0, le=10)


class DuckingModel(BaseModel):
    enabled: bool = False
    reduction_db: float = Field(default=16, ge=0, le=36)
    normal_db: float = Field(default=0, ge=-30, le=6)
    gap: float = Field(default=1.0, ge=0, le=5)
    pre: float = Field(default=.15, ge=0, le=1)
    post: float = Field(default=.25, ge=0, le=2)
    attack: float = Field(default=.15, ge=0, le=2)
    release: float = Field(default=.55, ge=0, le=3)
    segments: list[Segment] = Field(default_factory=list, max_length=1000)
    edited: bool = False


class TimelineModel(BaseModel):
    name: str = Field(default="未命名项目", max_length=100)
    duration: float = Field(gt=0, le=600)
    tracks: list[TrackModel] = Field(max_length=16)
    clips: list[ClipModel] = Field(default_factory=list, max_length=300)
    ducking: DuckingModel = Field(default_factory=DuckingModel)


class GenerateMusicOptions(BaseModel):
    mode: Literal["video", "text"] = "video"
    prompt: str = Field(default="", max_length=4100)
    duration_seconds: int = Field(default=30, ge=3, le=600)
    instrumental: bool = True
    reference_audio: bool = False


class MixdownOptions(BaseModel):
    timeline: TimelineModel
    stem: Literal["soundtrack", "music", "sfx", "full"] = "soundtrack"


def read_timeline(folder: Path) -> dict:
    path = folder / "timeline.json"
    if path.is_file():
        return json.loads(path.read_text())
    meta = json.loads((folder / "meta.json").read_text())
    return default_timeline(meta["duration"])


def speech_payload(folder: Path, duration: float, gap: float) -> dict:
    words_path = folder / "words.json"
    if not words_path.is_file():
        return {"recognized": False, "segments": [], "words": [], "text": ""}
    data = json.loads(words_path.read_text())
    segments = group_words(data.get("words", []), gap=gap, duration=duration)
    return {"recognized": True, "segments": [s.as_dict() for s in segments],
            "words": data.get("words", []), "text": data.get("text", "")}


@app.get("/api/projects/{job}")
def project_detail(job: str):
    folder = job_dir(job)
    meta = json.loads((folder / "meta.json").read_text())
    timeline = read_timeline(folder)
    return {**details(job, folder), "video_url": f"/api/file/{job}/video",
            "assets": [public_asset(job, a) for a in list_assets(folder)], "timeline": timeline,
            "speech": speech_payload(folder, meta["duration"], timeline.get("ducking", {}).get("gap", 1.0))}


@app.put("/api/projects/{job}/timeline")
def save_timeline(job: str, timeline: TimelineModel):
    folder = job_dir(job)
    (folder / "timeline.json").write_text(timeline.model_dump_json(indent=1))
    return {"ok": True}


@app.get("/api/projects/{job}/assets/{asset_id}")
def read_project_asset(job: str, asset_id: str, download: bool = False):
    item, path = asset_file(job_dir(job), asset_id)
    if not path.is_file():
        raise HTTPException(404, "Asset file missing")
    return FileResponse(path, filename=(item["name"] + path.suffix) if download else None)


@app.post("/api/projects/{job}/assets/upload")
def upload_project_asset(job: str, file: UploadFile = File(...), kind: str = Form("music")):
    folder = job_dir(job)
    if kind not in ("music", "sfx"):
        raise HTTPException(400, "kind must be music or sfx")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_AUDIO:
        raise HTTPException(400, "Expected MP3/WAV/M4A/AAC/FLAC/OGG")
    temp = folder / f"upload.pending{ext}"
    try:
        store_upload(file, temp)
        item = register_asset(folder, temp, kind, Path(file.filename or "音频").stem, "upload", move=True)
        return public_asset(job, item)
    except HTTPException:
        raise
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        temp.unlink(missing_ok=True)


@app.post("/api/projects/{job}/assets/generate-music")
def generate_project_music(job: str, opt: GenerateMusicOptions):
    folder = job_dir(job)
    pending = folder / "generate.pending.mp3"
    try:
        if opt.mode == "video":
            create_music(video_file(folder), pending, description=opt.prompt,
                         reference_audio=opt.reference_audio)
            name = "画面配乐 · " + (opt.prompt.strip()[:18] or "自动理解画面")
        else:
            if len(opt.prompt.strip()) < 3:
                raise HTTPException(422, "Prompt is too short")
            create_text_music(opt.prompt.strip(), pending, duration_seconds=opt.duration_seconds,
                              instrumental=opt.instrumental)
            name = "文字配乐 · " + opt.prompt.strip()[:18]
        item = register_asset(folder, pending, "music", name, opt.mode, prompt=opt.prompt, move=True, ext=".mp3")
        return public_asset(job, item)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        pending.unlink(missing_ok=True)


@app.post("/api/projects/{job}/assets/generate-sfx")
def generate_project_sfx(job: str, opt: SfxOptions):
    folder = job_dir(job)
    pending = folder / "generate.pending.mp3"
    try:
        create_sound_effect(opt.prompt.strip(), pending, duration_seconds=opt.duration_seconds, loop=opt.loop)
        item = register_asset(folder, pending, "sfx", "音效 · " + opt.prompt.strip()[:20], "text",
                              prompt=opt.prompt, move=True, ext=".mp3")
        return public_asset(job, item)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        pending.unlink(missing_ok=True)


@app.post("/api/projects/{job}/speech")
def trigger_speech(job: str, gap: float = 1.0, force: bool = False):
    """User clicked "智能人声避让". Recognition is billed only the first time (or when forced)."""
    if not (0 <= gap <= 5):
        raise HTTPException(422, "gap must be between 0 and 5")
    folder = job_dir(job)
    meta = json.loads((folder / "meta.json").read_text())
    if not meta.get("has_audio"):
        raise HTTPException(400, "This video has no dialogue audio; add speech ranges manually")
    cached = (folder / "words.json").is_file() and not force
    if not cached:
        try:
            payload = transcribe(video_file(folder))
        except Exception as exc:
            raise HTTPException(502, str(exc)) from exc
        (folder / "words.json").write_text(json.dumps(payload, ensure_ascii=False))
    return {"cached": cached, **speech_payload(folder, meta["duration"], gap)}


def _clip_inputs(folder: Path, tl: TimelineModel, kinds: set[str]) -> list[MixClip]:
    tracks = {t.id: t for t in tl.tracks}
    assets = {a["id"]: a for a in list_assets(folder)}
    result = []
    for clip in tl.clips:
        track = tracks.get(clip.track)
        if track is None:
            raise HTTPException(400, f"Clip {clip.id} references an unknown track")
        if track.kind not in kinds or track.mute:
            continue
        asset = assets.get(clip.asset)
        if asset is None:
            raise HTTPException(400, f"Clip {clip.id} references an unknown asset")
        if clip.offset >= asset["duration"]:
            raise HTTPException(400, f"Clip {clip.id} starts after the end of its audio")
        length = min(clip.length, asset["duration"] - clip.offset)
        result.append(MixClip(folder / "assets" / asset["file"], clip.start, clip.offset, length,
                              gain_db=clip.gain_db + track.volume_db + (tl.ducking.normal_db if track.kind == "music" else 0),
                              fade_in=clip.fade_in, fade_out=clip.fade_out, duck=track.duck))
    return result


@app.post("/api/projects/{job}/mixdown")
def mixdown(job: str, opt: MixdownOptions):
    folder = job_dir(job)
    meta = json.loads((folder / "meta.json").read_text())
    tl = opt.timeline
    duration = min(meta["duration"], tl.duration)
    kinds = {"soundtrack": {"music", "sfx"}, "music": {"music"}, "sfx": {"sfx"}, "full": {"music", "sfx"}}[opt.stem]
    clips = _clip_inputs(folder, tl, kinds)
    dialogue, dialogue_db = None, 0.0
    if opt.stem == "full" and meta.get("has_audio"):
        video_track = next((t for t in tl.tracks if t.kind == "video"), None)
        if video_track is None or not video_track.mute:
            dialogue = video_file(folder)
            dialogue_db = video_track.volume_db if video_track else 0.0
    segments = merge_segments([Segment(max(0, s.start), min(s.end, duration)) for s in tl.ducking.segments
                               if s.end > s.start and s.start < duration])
    out = folder / "exports" / f"{opt.stem}.wav"
    try:
        result = render_mix(clips, duration, out, segments=segments, ducking=tl.ducking.model_dump(),
                            dialogue=dialogue, dialogue_gain_db=dialogue_db)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    result.pop("rendered_file", None)
    return {**result, "stem": opt.stem, "url": f"/api/projects/{job}/exports/{opt.stem}.wav"}


@app.get("/api/projects/{job}/exports/{name}")
def read_export(job: str, name: str):
    if name not in {"soundtrack.wav", "music.wav", "sfx.wav", "full.wav"}:
        raise HTTPException(404, "Unknown export")
    path = job_dir(job) / "exports" / name
    if not path.is_file():
        raise HTTPException(404, "Export not ready")
    return FileResponse(path, filename=name, media_type="audio/wav")
