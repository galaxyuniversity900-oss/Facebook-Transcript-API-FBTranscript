"""Optional OpenAI-compatible hosted speech-recognition fallback.

Configured only through environment variables; no provider is contacted unless a key exists.
"""
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..extractors.facebook import FacebookExtractor
from ..models import Segment, Transcript


def _multipart_request(url: str, api_key: str, model: str, audio_path: Path,
                      language: str | None, translate: bool = False) -> dict:
    boundary = "----FBTranscriptBoundary7MA4YWxkTrZu0gW"
    fields = {"model": model, "response_format": "json"}
    if language:
        fields["language"] = language
    body = bytearray()
    for key, value in fields.items():
        body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n").encode())
    body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"audio{audio_path.suffix}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode())
    body.extend(audio_path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    request = urllib.request.Request(url, data=bytes(body), headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[-1200:]
        raise RuntimeError(f"Hosted speech API returned HTTP {exc.code}: {detail}") from exc


def transcribe_hosted(url: str, language: str | None = None,
                      translate_to: str | None = None) -> Transcript:
    providers = []
    if os.getenv("GROQ_API_KEY"):
        providers.append(("Groq", os.getenv("GROQ_API_KEY"),
                          os.getenv("FBTRANSCRIPT_GROQ_MODEL", "whisper-large-v3-turbo"),
                          os.getenv("FBTRANSCRIPT_GROQ_BASE_URL", "https://api.groq.com/openai/v1")))
    if os.getenv("OPENAI_API_KEY"):
        providers.append(("OpenAI", os.getenv("OPENAI_API_KEY"),
                          os.getenv("FBTRANSCRIPT_OPENAI_MODEL", "whisper-1"),
                          os.getenv("FBTRANSCRIPT_OPENAI_BASE_URL", "https://api.openai.com/v1")))
    if not providers:
        raise RuntimeError("No hosted speech provider configured (set GROQ_API_KEY or OPENAI_API_KEY).")
    errors = []
    with tempfile.TemporaryDirectory(prefix="fbtranscript-hosted-") as tmp:
        template = str(Path(tmp) / "audio.%(ext)s")
        info = FacebookExtractor().download_audio(url, template)
        audio = next((p for p in Path(tmp).iterdir() if p.is_file()), None)
        if audio is None:
            raise RuntimeError("Audio download produced no file for hosted recognition.")
        for name, key, model, base in providers:
            try:
                endpoint = base.rstrip("/") + "/audio/transcriptions"
                result = _multipart_request(endpoint, key, model, audio, language)
                text = (result.get("text") or "").strip()
                if not text:
                    raise RuntimeError("Provider returned an empty transcript.")
                duration = float(info.get("duration") or 0)
                translated_text = None
                if translate_to:
                    if translate_to != "en":
                        raise ValueError("Built-in hosted Whisper translation supports English only.")
                    translated = _multipart_request(base.rstrip("/") + "/audio/translations",
                                                    key, model, audio, None, True)
                    translated_text = (translated.get("text") or "").strip() or None
                return Transcript(
                    source_url=url, title=info.get("title"),
                    language=result.get("language") or language or "auto",
                    language_name=result.get("language") or language,
                    source=f"{name}:{model}",
                    segments=[Segment(start=0.0, duration=duration, text=text)],
                    warnings=[f"Recognition engine: hosted {name}"],
                    translated_text=translated_text,
                    translation_language="en" if translated_text else None,
                )
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
    raise RuntimeError("All configured hosted speech providers failed: " + " | ".join(errors))
