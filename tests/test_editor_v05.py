"""v0.5 editor API: asset library, multi-track timeline, user-triggered ducking, mixdown stems."""
from pathlib import Path
import array
import wave
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app
from core import MixClip, Segment, render_mix

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
client = TestClient(app)


def _rms(path: Path, start: float, end: float) -> float:
    with wave.open(str(path)) as w:
        rate, ch = w.getframerate(), w.getnchannels()
        w.setpos(int(start * rate))
        data = array.array("h", w.readframes(int((end - start) * rate)))
    return (sum(x * x for x in data) / max(1, len(data))) ** .5


def test_ducking_only_applies_when_enabled(tmp_path):
    clip = [MixClip(SAMPLES / "sample_music.mp3", 0, 0, 15, gain_db=-6, duck=True)]
    seg = [Segment(4, 8)]
    off = render_mix(clip, 15, tmp_path / "off.wav", segments=seg, ducking={"enabled": False})
    on = render_mix(clip, 15, tmp_path / "on.wav", segments=seg, ducking={"enabled": True, "reduction_db": 18})
    assert not off["ducking_applied"] and on["ducking_applied"]
    ratio_off = _rms(tmp_path / "off.wav", 5, 7) / _rms(tmp_path / "off.wav", 10, 12)
    ratio_on = _rms(tmp_path / "on.wav", 5, 7) / _rms(tmp_path / "on.wav", 10, 12)
    assert ratio_on < ratio_off * 0.35  # roughly -18 dB inside the speech window


def test_sample_project_is_an_editor_project():
    job = client.post("/api/sample").json()["job_id"]
    detail = client.get(f"/api/projects/{job}").json()
    kinds = sorted(a["kind"] for a in detail["assets"])
    assert kinds == ["music", "sfx"]
    tl = detail["timeline"]
    assert {t["kind"] for t in tl["tracks"]} == {"video", "music", "sfx"}
    assert len(tl["clips"]) == 2
    assert tl["ducking"]["enabled"] is False  # never applied until the user triggers it
    assert client.get(detail["assets"][0]["url"]).status_code == 200


def test_trigger_speech_is_cached_and_mixdown_stems():
    job = client.post("/api/sample").json()["job_id"]
    tl = client.get(f"/api/projects/{job}").json()["timeline"]
    with patch("app.transcribe", side_effect=AssertionError("cached sample must not be billed")):
        speech = client.post(f"/api/projects/{job}/speech?gap=1.0")
    assert speech.status_code == 200, speech.text
    assert speech.json()["cached"] and len(speech.json()["segments"]) == 3
    tl["ducking"].update(enabled=True, segments=speech.json()["segments"])
    assert client.put(f"/api/projects/{job}/timeline", json=tl).status_code == 200
    for stem in ("soundtrack", "music", "sfx", "full"):
        r = client.post(f"/api/projects/{job}/mixdown", json={"timeline": tl, "stem": stem})
        assert r.status_code == 200, r.text
        assert r.json()["ducking_applied"] is (stem != "sfx")
        wav = client.get(r.json()["url"])
        assert wav.status_code == 200 and wav.content[:4] == b"RIFF"
    assert client.get(f"/api/projects/{job}/exports/../../meta.json").status_code == 404


def test_generated_and_uploaded_assets_join_library():
    job = client.post("/api/sample").json()["job_id"]

    def fake_sfx(prompt, output, *, duration_seconds, loop):
        output.write_bytes((SAMPLES / "sample_sfx_whoosh.mp3").read_bytes())

    def fake_music(video, output, *, description, reference_audio):
        output.write_bytes((SAMPLES / "sample_music.mp3").read_bytes())

    with patch("app.create_sound_effect", fake_sfx), patch("app.create_music", fake_music):
        s = client.post(f"/api/projects/{job}/assets/generate-sfx", json={"prompt": "door slam", "duration_seconds": 2})
        m = client.post(f"/api/projects/{job}/assets/generate-music", json={"mode": "video"})
    assert s.status_code == 200 and s.json()["kind"] == "sfx", s.text
    assert m.status_code == 200 and m.json()["kind"] == "music", m.text
    with (SAMPLES / "sample_sfx_whoosh.mp3").open("rb") as f:
        u = client.post(f"/api/projects/{job}/assets/upload", files={"file": ("hit.mp3", f, "audio/mpeg")},
                        data={"kind": "sfx"})
    assert u.status_code == 200 and u.json()["name"] == "hit"
    assert len(client.get(f"/api/projects/{job}").json()["assets"]) == 5
    bad = client.post(f"/api/projects/{job}/mixdown", json={"timeline": {
        "duration": 15, "tracks": [{"id": "m", "kind": "music"}],
        "clips": [{"id": "x", "track": "m", "asset": "0" * 32, "start": 0, "length": 3}]}})
    assert bad.status_code == 400
