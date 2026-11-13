"""Build static/index.html (served by FastAPI) and the single-file offline preview.

Usage: python3 scripts/build_frontend.py
The sample media is embedded so the page also works when opened directly from disk.
"""
from pathlib import Path
import base64
import json

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "frontend"
S = ROOT / "samples"


def b64(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


html = (FE / "index.template.html").read_text(encoding="utf-8")
html = html.replace("/*__STYLES__*/", (FE / "styles.css").read_text(encoding="utf-8"))
html = html.replace("/*__APP__*/", (FE / "app.js").read_text(encoding="utf-8"))
html = html.replace("__SAMPLE_VIDEO__", b64(S / "sample_video.mp4", "video/mp4"))
html = html.replace("__SAMPLE_MUSIC__", b64(S / "sample_music.mp3", "audio/mpeg"))
html = html.replace("__SAMPLE_SFX__", b64(S / "sample_sfx_whoosh.mp3", "audio/mpeg"))
html = html.replace("/*__SAMPLE_WORDS__*/null", json.dumps(json.loads((S / "sample_words.json").read_text()), ensure_ascii=False))
(ROOT / "static" / "index.html").write_text(html, encoding="utf-8")
(ROOT / "SoundFlow_Studio_v0.5_交互预览.html").write_text(html, encoding="utf-8")
print("built", len(html) // 1024, "KB")
