# FBTranscript

A local-first Facebook video transcription toolkit with a lightweight Android/Termux runtime. It retrieves subtitle tracks exposed by yt-dlp and can optionally use local faster-whisper speech recognition.

> Use only videos you own or are authorized to access. This project does not bypass private-video permissions, login walls, DRM, or platform restrictions. Availability depends on Facebook, your account permissions, video visibility, and yt-dlp compatibility.

## Android / Termux (recommended lightweight mode)

The Android runtime uses Python's standard-library HTTP server and SQLite. It does **not** install FastAPI, Uvicorn, Pydantic, Rust, FFmpeg, or Whisper. This avoids several native-wheel/build problems common on Android and keeps the default installation small.

In Termux, run:

    pkg update -y
    pkg install -y git python
    git clone https://github.com/galaxyuniversity900-oss/Facebook-Transcript-API-FBTranscript.git
    cd Facebook-Transcript-API-FBTranscript
    bash scripts/install-termux.sh

Start the app:

    ~/bin/fbtranscript

Open in the Android browser:

    http://127.0.0.1:8787

Keep the Termux session open while using the app. Stop the server with Ctrl+C. The launcher uses a local-only bind address by default; do not expose it to public networks.

The installer creates an isolated Python virtual environment, installs only the lightweight package dependencies, and creates `~/bin/fbtranscript`.

## Android runtime behavior

- Lightweight captions-first extraction; Whisper is unchecked and disabled by default.
- Existing browser interface, transcript history, batch queue, retry, and TXT/JSON/SRT/VTT/HTML export endpoints.
- SQLite history stored at `~/.fbtranscript/jobs.sqlite3`.
- One background transcription worker to limit phone CPU and memory use.
- No root access and no Android APK required.
- The Android server is local to the phone at `127.0.0.1`.
- FFmpeg is not needed for caption extraction. Install it separately only if you later configure audio/Whisper fallback.

## Desktop / API installation

Python 3.10+:

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[api]"
    uvicorn fbtranscript.api:app --host 127.0.0.1 --port 8787

Open `http://127.0.0.1:8787`; API docs at `/docs`.

## Optional Whisper

Whisper is intentionally not part of the Android install. It can require native dependencies, FFmpeg, model downloads, substantial storage, RAM, and CPU time. On supported desktop systems:

    python -m pip install -e ".[whisper]"

## Features

- Manual and automatic caption tracks when exposed by Facebook/yt-dlp.
- Arabic and English subtitle preferences.
- Timestamped segments; TXT, JSON, SRT, VTT, and HTML output.
- FastAPI REST API (desktop), Android standard-library HTTP runtime, browser UI, and CLI.
- SQLite job history, batch processing (up to 25 URLs), retry, and interrupted-job recovery.
- No mandatory hosted service or subscription.

## CLI

    fbtranscript 'https://www.facebook.com/watch/?v=VIDEO_ID' --format srt -o output.srt
    fbtranscript 'https://www.facebook.com/watch/?v=VIDEO_ID' --captions-only --format json

## Authorized cookies

Some videos may require an authenticated session. If you are authorized to view the content, set `FBTRANSCRIPT_COOKIE_FILE` to a Netscape-format cookies file. Treat it like a password; never commit or share it. This does not defeat access controls.

## Project layout

- `fbtranscript/android.py` — lightweight Android/Termux HTTP server.
- `fbtranscript/extractors/facebook.py` — caption retrieval and audio download.
- `fbtranscript/engines/whisper.py` — optional local speech recognition.
- `fbtranscript/service.py` — captions-first orchestration.
- `fbtranscript/formatters.py` — export serializers.
- `fbtranscript/api.py` — optional FastAPI desktop service.
- `fbtranscript/web/` — browser interface.
- `scripts/install-termux.sh` — Termux installer.
- `tests/` — offline unit tests.

## Limitations

Facebook does not expose captions for every video. yt-dlp support can change when Facebook changes its site. Captions may be absent, inaccessible, or in an unexpected language. Whisper is an optional fallback, not a way to retrieve access-restricted captions. The Android runtime is a local single-user service, not a public production server.

## Development

    python -m pip install -e ".[dev]"
    pytest
