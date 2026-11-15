# ElevenLabs-Video-Audio-Studio

**A soundtrack timeline that gives motion-comic dialogue room to breathe.**

English · [简体中文（默认）](README.md) · Editor version v0.5

SoundFlow Studio is a locally hosted soundtrack and sound-effects editor. Generate or import audio, arrange it on a multitrack timeline, and lower the music when a character speaks. Export stems back to your video editor for the final cut.

## Built for these creative moments

| Workflow | How it helps |
|---|---|
| Motion comics / animated panels | Keep dialogue intelligible while retaining the musical mood |
| Narrative shorts | Place suspense beds, transitions, and emotional lifts on separate tracks |
| Product films / design reels | Generate a musical starting point, then trim and fade it to match the edit |
| A series of clips | Import a batch and refine individual projects on an editable timeline |

## What works today

- Multitrack music, sound effects, and source dialogue; drag, trim, split, delete, set volume, fade, and snap.
- Per-track mute and ducking controls; editable speech ranges, attenuation, pre-roll, hold, and release.
- ElevenLabs music from text or video, sound effects from text, and existing-audio imports.
- Scribe recognition when you explicitly request speech ducking; reuse cached recognition unless you force a new request.
- Web Audio preview, before/after comparison, undo/redo, and autosave.
- WAV soundtrack, music stem, SFX stem, full listening mix, and timeline JSON exports.

**The v0.5 editor delivers audio and project data. Its export workflow does not render a final MP4. Bring the WAV files into CapCut, Premiere, DaVinci Resolve, or your preferred editor.**

> The application UI is currently primarily in Chinese; this README provides English setup and workflow instructions.

## Stack & requirements

| Layer | Implementation |
|---|---|
| Frontend | Vanilla HTML / CSS / JavaScript, Canvas timeline, Web Audio API |
| Local backend | Python, FastAPI, Uvicorn, Pydantic |
| API client | HTTPX → ElevenLabs Music, Sound Effects, Scribe |
| Media | FFmpeg / ffprobe; local WAV rendering |
| Storage | Local `runtime/` files, project metadata, and timeline JSON; no database |
| Recommended setup | Python 3.11 / 3.12, FFmpeg, desktop browser; macOS / Linux / Windows |

## Quick start

Download or clone this repository and open a terminal in its root, containing `app.py` and `requirements.txt`. The existing folder is named `SoundFlow_Studio_v0.5`.

### Install dependencies

Use Python **3.11 or 3.12** and a separate virtual environment for this project. This is a Python application: **Node.js, npm, and an external database are not required**. Use a recent Chrome, Edge, Firefox, or Safari; media decoding depends on the browser.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` directly and use that Python executable for subsequent commands.

Install FFmpeg, for example:

```bash
# macOS with Homebrew
brew install ffmpeg
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install ffmpeg
```

On Windows, install FFmpeg and add its `bin` directory to PATH. Open a new terminal and check:

```bash
ffmpeg -version
ffprobe -version
```

### Configure & run

The included sample and local editing do not require an API key. For live AI generation or recognition, set the variable in the terminal that starts the server:

```bash
export ELEVENLABS_API_KEY="<your-elevenlabs-api-key>"
python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

PowerShell:

```powershell
$env:ELEVENLABS_API_KEY="<your-elevenlabs-api-key>"
python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

Open **http://127.0.0.1:8765**. Local API documentation: **http://127.0.0.1:8765/api/docs**. On macOS, you can also run `./启动_Mac.command` from a terminal with the variable configured.

| Variable | Purpose |
|---|---|
| `ELEVENLABS_API_KEY` | Required for AI calls, with appropriate product access and quota |
| `DUCKING_DATA_DIR` | Optional local job directory; defaults to the repository's `runtime/` |

**The backend does not automatically load `.env`.** Copying `.env.example` alone does not configure it; use environment variables as shown above. Keep real keys out of Git.

### Make your first edit without an API call

1. Open the included sample and inspect its speech ranges.
2. Move the music, adjust volume, and compare playback with ducking enabled.
3. Add a transition sound effect and adjust its fades.
4. Export a soundtrack WAV, stems, or timeline JSON for your editing workflow.

You can also open `SoundFlow_Studio_v0.5_交互预览.html` directly for an offline sample editor. Offline preview does not generate AI media; recognition of new footage requires the backend and API.

## A prompt for a motion-comic scene

> A 20-second suspense bed for a motion comic. Restrained opening, plenty of space under dialogue, tension rising over the last four seconds. Instrumental; avoid a busy lead melody. Keep transition effects separate from the music.

Listen against the actual edit and align cues and speech ranges by hand. Generated music is not guaranteed to hit every cut.

## Data, costs & limits

| Action | Data destination / cost |
|---|---|
| Import, timeline editing, FFmpeg rendering | Local processing; no ElevenLabs request needed |
| Video-to-music | Video and description sent to ElevenLabs; usage may be billed |
| Scribe recognition | Video file, including its audio and imagery, sent to ElevenLabs; usage may be billed |
| Text music / sound effects | Prompt sent to ElevenLabs; usage may be billed |

The backend reads the key from the environment and sends it to ElevenLabs in HTTPS authentication headers. The browser receives only configuration status. `runtime/`, `.env`, and virtual environments are ignored by Git. Local hosting does not mean AI requests stay on the device or that upstream retention is disabled.

A source video is currently limited to **100 MB / 600 seconds**. Music already mixed into the source is not separated or removed; ducking controls tracks added here. Review automatic speech detection. There is no login, multitenancy, or automatic job cleanup. Verify rights for sample media and your own outputs separately.

## Development map

| Path | Role |
|---|---|
| `app.py` | Projects, assets, recognition, and export endpoints |
| `core.py` | Speech intervals, FFmpeg mixing, media probing |
| `elevenlabs_client.py` | Music / Scribe / Sound Effects requests |
| `frontend/` | Editor source |
| `static/index.html` | Built page served by the backend |
| `fc_worker.py` | Reusable mix worker; no cloud deployment implied |

After frontend changes, run `python scripts/build_frontend.py`. Developer checks: `python -m pytest -q`. Mocked tests do not validate a live account's API access.

## References

- [ElevenLabs Video-to-Music](https://elevenlabs.io/docs/api-reference/music/video-to-music)
- [ElevenLabs Scribe transcription](https://elevenlabs.io/docs/api-reference/speech-to-text/convert)
- [FFmpeg documentation](https://ffmpeg.org/documentation.html)

## Local deployment & development

The commands above start a **single-user service on your own machine**. Leave the terminal running and press `Ctrl+C` to stop it. To restart, enter the same directory, activate the same environment, and run the start command again. If another project uses the port, stop it or choose a different `--port`.

A process manager can keep the same Uvicorn command running. Before offering this service to a team or the public, add authentication, user isolation, a job queue, usage limits, redacted logs, and file cleanup. These production deployment features are not implemented here.

## Troubleshooting

| Symptom | What to check |
|---|---|
| Missing `uvicorn` or Python module | Activate the virtual environment; run `python -m pip install -r requirements.txt` from the project root |
| FFmpeg missing / media probe fails | Check `ffmpeg -version` and `ffprobe -version`; reopen the terminal after installation |
| API returns 401 / 403 | Check the local key, product permissions, and account status; never paste a full key into an issue |
| API returns 429 / generation times out | Check quota, concurrency, and network access; start with a short clip and inspect upstream job state before resubmitting |
| Preview does not play | Check browser codec support; download the result and try a local player |
| Environment changes do not take effect | Restart Uvicorn from the terminal where the variables are configured |

## Contributing

Reproduction steps, sanitized errors, and feature suggestions are welcome. A concrete case—music masking comic dialogue, subtitle drift after dubbing, or an unsuitable musical mood—is especially useful. Include OS, Python / FFmpeg versions, media format, and a minimal workflow. Confirm sharing rights before providing real media.

Code is provided under the [MIT License](LICENSE). API terms, generated-content rights, media-asset rights, and dependency licenses apply separately.

## ElevenLabs integration & pricing inquiries

Maintained by an independent developer, this project gives motion-comic teams, video creators, and builders a practical way to explore ElevenLabs.

Working on **motion-comic dubbing, short-drama localization, video soundtracks, sound effects, voice products, or batch API integration**? Get in touch to discuss product fit, workflow design, and integration. I can also offer **competitively priced ElevenLabs solutions**; availability, terms, and pricing depend on your requirements and an individual quotation.

**Email: [lcnwys@gmail.com](mailto:lcnwys@gmail.com)**

For a useful first conversation, include:

- Your content or product type and a short, sanitized description of the requirement.
- Estimated monthly audio/video minutes, target languages, team size, and API needs.
- Whether you are testing a pilot or preparing a launch.

Do not send API keys, passwords, or unauthorized customer media by email or in public issues. Use issues for product feedback and email for commercial inquiries.

> An independent community project, not an official ElevenLabs product. Inquiries and quotations do not imply official endorsement. ElevenLabs names and trademarks belong to their respective owners.
