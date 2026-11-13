"""The only module that talks to ElevenLabs. No secrets ever returned to browsers."""
from __future__ import annotations

from pathlib import Path
import io
import mimetypes
import os
import zipfile

import httpx

API_BASE = "https://api.elevenlabs.io/v1"


def _key() -> str:
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured on the server")
    return key


def create_music(video: Path, output: Path, *, description: str = "", reference_audio: bool = False) -> None:
    """Only pure music in v1 demo; preserve original video audio through FFmpeg mixing."""
    headers = {"xi-api-key": _key()}
    fields = {
        "model_id": "music_v2_5",
        "add_sfx": "false",
        "separate_tracks": "false",
        "use_audio_as_reference": "true" if reference_audio else "false",
    }
    if description.strip():
        fields["description"] = description.strip()[:4100]
    mime = mimetypes.guess_type(video.name)[0] or "application/octet-stream"
    with open(video, "rb") as source, httpx.Client(timeout=httpx.Timeout(300.0, connect=20)) as client:
        response = client.post(f"{API_BASE}/music/video-to-music", headers=headers, data=fields,
                               files={"videos[]": (video.name, source, mime)})
    if response.status_code >= 400:
        raise RuntimeError(f"ElevenLabs Music HTTP {response.status_code}: {response.text[:650]}")
    if len(response.content) > 100 * 1024 * 1024:
        raise RuntimeError("Generated soundtrack too large")
    mime_out = response.headers.get("content-type", "").lower()
    if response.content[:4] == b"PK\x03\x04" or "zip" in mime_out:
        # Default separate_tracks is false. Do not guess which track is music when archive is unexpected.
        raise RuntimeError("Video-to-Music unexpectedly returned ZIP; demo expects a single MP3 track")
    if "json" in mime_out:
        raise RuntimeError("ElevenLabs returned JSON instead of music audio")
    output.write_bytes(response.content)


def transcribe(video: Path) -> dict:
    fields = {"model_id": "scribe_v2", "timestamps_granularity": "word",
              "tag_audio_events": "true", "diarize": "false"}
    mime = mimetypes.guess_type(video.name)[0] or "application/octet-stream"
    with open(video, "rb") as source, httpx.Client(timeout=httpx.Timeout(300.0, connect=20)) as client:
        response = client.post(f"{API_BASE}/speech-to-text", headers={"xi-api-key": _key()},
                               data=fields, files={"file": (video.name, source, mime)})
    if response.status_code >= 400:
        raise RuntimeError(f"ElevenLabs Scribe HTTP {response.status_code}: {response.text[:650]}")
    payload = response.json()
    if not isinstance(payload.get("words"), list):
        raise RuntimeError("Scribe response has no words array")
    return payload


def _write_audio_response(response: httpx.Response, output: Path) -> None:
    if response.status_code >= 400:
        raise RuntimeError(f"ElevenLabs HTTP {response.status_code}: {response.text[:500]}")
    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type or response.content[:4] == b"PK\x03\x04":
        raise RuntimeError("Expected an audio file, but received a different response")
    if not response.content or len(response.content) > 100 * 1024 * 1024:
        raise RuntimeError("Invalid size of generated audio")
    output.write_bytes(response.content)


def create_text_music(prompt: str, output: Path, *, duration_seconds: int = 30,
                      instrumental: bool = True) -> None:
    """Generate standalone music: separate from video soundtracks and sound effects."""
    headers = {"xi-api-key": _key(), "Content-Type": "application/json"}
    payload = {"prompt": prompt, "model_id": "music_v2_5",
               "music_length_ms": duration_seconds * 1000,
               "force_instrumental": instrumental}
    with httpx.Client(timeout=httpx.Timeout(300.0, connect=20)) as client:
        response = client.post(f"{API_BASE}/music", headers=headers, json=payload)
    _write_audio_response(response, output)


def create_sound_effect(prompt: str, output: Path, *, duration_seconds: float = 5,
                        loop: bool = False) -> None:
    """Generate one standalone SFX file, with no background-music mixing."""
    headers = {"xi-api-key": _key(), "Content-Type": "application/json"}
    payload = {"text": prompt, "model_id": "eleven_text_to_sound_v3",
               "duration_seconds": duration_seconds, "loop": loop}
    with httpx.Client(timeout=httpx.Timeout(300.0, connect=20)) as client:
        response = client.post(f"{API_BASE}/sound-generation", headers=headers, json=payload)
    _write_audio_response(response, output)
