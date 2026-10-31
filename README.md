# FBTranscript

A local-first Facebook video transcription toolkit. The primary workflow downloads the actual video audio and runs speech recognition (ASR); page descriptions and written captions are not treated as spoken transcript.

> Use only videos you own or are authorized to access. This project does not bypass private-video permissions, login walls, DRM, or platform restrictions. Availability depends on Facebook, your account permissions, video visibility, and yt-dlp compatibility.

## Android / Termux

The Android runtime uses Python's standard-library HTTP server and SQLite. Install the base app, then install the native Whisper speech engine and its multilingual tiny model:

    bash scripts/install-termux.sh
    bash scripts/install-whisper-termux.sh

Start the app:

    ~/bin/fbtranscript

Open in the Android browser:

    http://127.0.0.1:8787

Keep Termux open while using the app. Stop the server with Ctrl+C. The service binds to 127.0.0.1 by default.

The Whisper setup compiles whisper.cpp locally and downloads a model. It requires build tools, free storage, battery, RAM, and time. The default tiny model is multilingual; larger models can improve recognition at higher resource cost.

## Android runtime behavior

- Audio-first: downloads the video's audio, converts it to 16 kHz mono WAV with FFmpeg, then runs whisper.cpp.
- Never silently substitutes captions, descriptions, or post text when speech recognition fails.
- Multilingual speech recognition with automatic language detection by default; manually pin Arabic or English when the audio is known to use one language.
- Mixed-language speech can be transcribed by the multilingual model, but Whisper does not reliably label every language switch inside a single recording; the reported language is the detected dominant/initial language.
- Optional second-pass translation of the recognized speech into English. Original transcript is retained separately. Whisper built-in translation targets English only; arbitrary target languages require a separately configured translation provider.
- Timestamps, TXT/JSON/SRT/VTT/HTML export.
- SQLite history at ~/.fbtranscript/jobs.sqlite3, batch jobs, retry, and recovery.
- Multi-profile extraction: tries multiple yt-dlp audio/video format strategies with retries before reporting extraction failure.
- Recognition fallback chain: native whisper.cpp first, optional faster-whisper next when installed, then configured NVIDIA Speech NIM ASR endpoints with endpoint-scoped model discovery. Each provider is attempted only when its credentials are configured.
- NVIDIA fallback is optional and sends the downloaded audio to the configured Speech NIM endpoint; local-only processing remains the default when no API key is set.
- Hosted recognition can preserve provider segment timestamps when returned. Some providers return only full-text results, in which case the transcript is represented as one segment.
- One background worker to limit phone CPU and memory use.
- No root access and no APK required; the UI runs locally in the Android browser.

## Desktop / API installation

Python 3.10+:

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -e ".[api]"
    uvicorn fbtranscript.api:app --host 127.0.0.1 --port 8787

Optional desktop faster-whisper:

    python -m pip install -e ".[whisper]"

## CLI

    fbtranscript 'https://www.facebook.com/watch/?v=VIDEO_ID' --format srt -o output.srt
    fbtranscript 'https://www.facebook.com/watch/?v=VIDEO_ID' --translate-to en --format json
    fbtranscript 'https://www.facebook.com/watch/?v=VIDEO_ID' --captions-only --format json

### Optional NVIDIA Speech NIM recognition

Local engines require no API key. To enable a remote fallback when local engines are unavailable, configure one or both providers in Termux before starting the app:

    export GROQ_API_KEY="your_groq_api_key"
    # or
    export OPENAI_API_KEY="your_openai_api_key"

Optional model overrides:

    export FBTRANSCRIPT_GROQ_MODEL="whisper-large-v3-turbo"
    export FBTRANSCRIPT_GROQ_TRANSLATION_MODEL="whisper-large-v3"
    export FBTRANSCRIPT_OPENAI_MODEL="whisper-1"

Groq is attempted before OpenAI when both keys are present. Audio is uploaded to the provider; review its privacy and retention terms before enabling it. Never place API keys in the repository or share them in logs.

## Authorized cookies

Some videos may require an authenticated session. If you are authorized to view the content, set FBTRANSCRIPT_COOKIE_FILE to a Netscape-format cookies file. Treat it like a password; never commit or share it. This does not defeat access controls.

## Project layout

- fbtranscript/android.py — lightweight Android/Termux HTTP server.
- fbtranscript/extractors/facebook.py — authorized video audio download and optional caption retrieval.
- fbtranscript/engines/whisper.py — whisper.cpp / faster-whisper ASR integration.
- fbtranscript/service.py — audio-first orchestration.
- fbtranscript/formatters.py — export serializers.
- fbtranscript/web/ — browser interface.
- scripts/install-termux.sh — base Termux installer.
- scripts/install-whisper-termux.sh — native speech engine and model setup.

## Limitations

Facebook/yt-dlp support can change when Facebook changes its site. Some videos may be unavailable without an authorized login session. Audio transcription quality depends on audio clarity, language, accents, and model size. The Android runtime is a local single-user service, not a public production server.

## Development

    python -m pip install -e ".[dev]"
    pytest
