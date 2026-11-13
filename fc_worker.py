"""Reusable local FFmpeg executor contract for the proposed FC adapter.

The current CLI is intentionally NOT a deployed FC HTTP/event handler and does not use OSS.
Future FC handler should download OSS objects to /tmp, call execute(), upload output to OSS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from core import MixClip, Segment, render_mix, render_video


def execute(manifest: dict, working_dir: Path) -> dict:
    """Run from local relative paths (not public URLs), isolate filesystem via working_dir."""
    base = working_dir.resolve()
    def resolve_relative(value: str) -> Path:
        p = (base / value).resolve()
        if not p.is_relative_to(base):
            raise ValueError("File path must be relative to working_dir")
        return p
    if manifest.get("type") == "mixdown":
        # v0.5 editor timeline: audio-only stems, CPU only, no video encoding.
        out = resolve_relative(manifest["local_output"])
        clips = [MixClip(resolve_relative(c["local_file"]), float(c["start"]), float(c.get("offset", 0)),
                         float(c["length"]), float(c.get("gain_db", 0)), float(c.get("fade_in", 0)),
                         float(c.get("fade_out", 0)), bool(c.get("duck", False))) for c in manifest["clips"]]
        segments = [Segment(float(s["start"]), float(s["end"])) for s in manifest.get("speech_segments", [])]
        dialogue = resolve_relative(manifest["local_dialogue"]) if manifest.get("local_dialogue") else None
        return render_mix(clips, float(manifest["duration"]), out, segments=segments,
                          ducking=manifest.get("ducking", {}), dialogue=dialogue,
                          dialogue_gain_db=float(manifest.get("dialogue_gain_db", 0)))
    video = resolve_relative(manifest["local_video"])
    music = resolve_relative(manifest["local_music"])
    out = resolve_relative(manifest["local_output"])
    out.parent.mkdir(parents=True, exist_ok=True)
    segments = [Segment(float(s["start"]), float(s["end"])) for s in manifest["speech_segments"]]
    mix = manifest.get("mix", {})
    return render_video(video, music, out, segments,
                        reduction_db=float(mix.get("reduction_db", 16)),
                        normal_music_db=float(mix.get("normal_music_db", -12)),
                        pre=float(mix.get("pre", .15)), post=float(mix.get("post", .25)),
                        attack=float(mix.get("attack", .15)), release=float(mix.get("release", .55)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run local FFmpeg executor on a JSON job manifest")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--workdir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    print(json.dumps(execute(data, args.workdir), ensure_ascii=False, indent=2))
