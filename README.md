# FBTranscript

A local-first Facebook video transcription toolkit. It retrieves subtitle tracks exposed for a video by yt-dlp and can optionally fall back to local speech recognition with faster-whisper.

> Use only videos you own or are authorized to access. This project does not bypass private-video permissions, login walls, DRM, or platform restrictions. Actual availability depends on Facebook, your account permissions, the video's visibility, and yt-dlp compatibility.

## Features
- Captions-first extraction (manual and automatic tracks when exposed).
- Optional local faster-whisper speech-to-text fallback.
- Arabic and English subtitle preferences; Whisper language auto-detection or a language hint.
- Timestamped segments; TXT, JSON, SRT, VTT, and HTML output.
- FastAPI REST API, browser UI, and command-line interface.
- No mandatory hosted service or subscription.

## Requirements
- Python 3.10 or newer.
- Internet connection for source retrieval.
- FFmpeg recommended; required by some audio formats and workflows.
- Whisper is optional and can consume significant storage, RAM, CPU time, and model download bandwidth.

## Install
    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .
    # Optional local speech recognition:
    python -m pip install -e ".[whisper]"

On Termux, install Python and FFmpeg with the Termux package manager first. For low-memory phones, try Whisper model tiny or base. Device performance and package compatibility vary.

## Start the web app
    uvicorn fbtranscript.api:app --host 127.0.0.1 --port 8787

Open http://127.0.0.1:8787. Interactive API documentation: http://127.0.0.1:8787/docs.

## REST API
Health:
    curl http://127.0.0.1:8787/api/v1/health

Transcribe:
    curl -X POST http://127.0.0.1:8787/api/v1/transcribe \
      -H 'Content-Type: application/json' \
      -d '{"url":"https://www.facebook.com/watch/?v=VIDEO_ID","languages":["ar","en","all"],"whisper":true,"model_size":"small"}'

Export by posting the same request body to /api/v1/export/txt, /json, /srt, /vtt, or /html.

## CLI
    fbtranscript 'https://www.facebook.com/watch/?v=VIDEO_ID' --format srt -o output.srt
    fbtranscript 'https://www.facebook.com/watch/?v=VIDEO_ID' --captions-only --format json
    fbtranscript 'https://www.facebook.com/watch/?v=VIDEO_ID' --language ar --model tiny

## Authorized cookies
Some videos may require an authenticated session. If you are authorized to view that content, set FBTRANSCRIPT_COOKIE_FILE to a Netscape-format cookies file:
    export FBTRANSCRIPT_COOKIE_FILE=/absolute/path/to/cookies.txt

Treat the cookies file like a password. Never commit or share it. This option does not defeat access controls; it supplies your own authorized session to yt-dlp. Follow Facebook terms and applicable law.

## Project layout
- fbtranscript/extractors/facebook.py — caption retrieval and audio download.
- fbtranscript/engines/whisper.py — optional local speech recognition.
- fbtranscript/service.py — captions-first orchestration.
- fbtranscript/formatters.py — export serializers.
- fbtranscript/api.py — REST API and web entry point.
- fbtranscript/cli.py — CLI.
- fbtranscript/web/ — browser interface.
- tests/ — offline unit tests.


## Background jobs, batches, and history

Long jobs can be submitted without holding the HTTP request open:

    curl -X POST http://127.0.0.1:8787/api/v1/jobs \
      -H 'Content-Type: application/json' \
      -d '{"url":"https://www.facebook.com/watch/?v=VIDEO_ID","whisper":true}'

The response includes a job ID. Check its state at /api/v1/jobs/JOB_ID and retrieve the transcript from /api/v1/jobs/JOB_ID/result when status is completed. List recent jobs at /api/v1/jobs. Retry a failed job with POST /api/v1/jobs/JOB_ID/retry.

For a batch, send up to 25 video URLs to POST /api/v1/jobs/batch:

    curl -X POST http://127.0.0.1:8787/api/v1/jobs/batch \
      -H 'Content-Type: application/json' \
      -d '{"urls":["https://www.facebook.com/watch/?v=ID1","https://www.facebook.com/watch/?v=ID2"],"whisper":false}'

Job metadata and transcript results are stored in SQLite. By default the database is ~/.fbtranscript/jobs.sqlite3. Set FBTRANSCRIPT_DB to choose another path. If the process stops while a job is running, the next startup marks that job failed so it can be retried. The in-process background worker is suitable for a local single-user service; it is not a distributed queue for multi-worker production deployments.

## Known limitations
Facebook does not expose captions for every video. yt-dlp support can change when Facebook changes its site. Captions may be absent, inaccessible, or in an unexpected language. Whisper is a speech-recognition fallback, not a way to retrieve access-restricted captions. This initial implementation handles a request synchronously; persistent job queues, batch processing, resumable jobs, and history storage are not included yet.

## Development
    python -m pip install -e ".[dev]"
    pytest

## License
See LICENSE.
