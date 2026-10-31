"""NVIDIA Speech NIM hosted ASR with endpoint-scoped model discovery.

No global NVIDIA catalog endpoint is assumed. Configure one or more actual Speech NIM
base URLs / NVCF invocation URLs in FBTRANSCRIPT_NVIDIA_ASR_ENDPOINTS.
"""
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from ..extractors.facebook import FacebookExtractor
from ..models import Segment, Transcript

# Only known speech-recognition families are eligible. TTS, LLM and translation-only
# model names are deliberately excluded from automatic ASR selection.
_ASR_FAMILIES = {
    "whisper": {"languages": "multilingual", "rank": 10},
    "canary": {"languages": "multilingual", "rank": 20},
    "parakeet-tdt-0.6b": {"languages": "european", "rank": 30},
    "parakeet-ctc": {"languages": "european", "rank": 31},
    "parakeet-1.1b-rnnt-multilingual": {"languages": "multilingual-25", "rank": 32},
    "nemotron-asr": {"languages": "english", "rank": 40},
}
_NON_ASR = ("tts", "text-to-speech", "magpie", "fastpitch", "llama", "mistral",
            "deepseek", "qwen", "embed", "rerank", "translation", "nmt")


def _endpoint_urls() -> list[str]:
    raw = os.getenv("FBTRANSCRIPT_NVIDIA_ASR_ENDPOINTS", "")
    values = [item.strip().rstrip("/") for item in raw.split(";") if item.strip()]
    # NVIDIA_API_KEY alone is not enough to infer a hosted Speech NIM URL.
    return list(dict.fromkeys(values))


def _api_url(base: str, path: str) -> str:
    if base.endswith(path):
        return base
    if base.endswith("/v1"):
        return base + path.removeprefix("/v1")
    return base + path


def _http_json(url: str, api_key: str, timeout: int = 20) -> dict:
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}", "Accept": "application/json",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8", "replace")
    value = json.loads(payload)
    return value if isinstance(value, dict) else {}


def _model_ids(payload: dict) -> list[str]:
    ids = []
    for item in payload.get("data", []) if isinstance(payload.get("data"), list) else []:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    for item in payload.get("modelInfo", []) if isinstance(payload.get("modelInfo"), list) else []:
        if isinstance(item, dict):
            name = item.get("shortName") or item.get("modelUrl")
            if name:
                ids.append(str(name).rsplit("/", 1)[-1])
    return list(dict.fromkeys(ids))


def _family(model_id: str) -> tuple[str, dict] | None:
    name = model_id.lower()
    if any(token in name for token in _NON_ASR):
        return None
    for family, meta in _ASR_FAMILIES.items():
        if family in name:
            return family, meta
    return None


def _supports_language(meta: dict, language: str | None) -> bool:
    lang = (language or "").lower().split("-", 1)[0]
    support = meta["languages"]
    if not lang:
        return True
    if support == "multilingual":
        return True
    if support == "multilingual-25":
        # Parakeet's commonly published 25-language set is European; Arabic is not included.
        return lang in {"en", "de", "es", "fr", "it", "pt", "nl", "pl", "ru", "uk",
                        "cs", "sk", "sl", "hr", "bg", "et", "fi", "el", "hu", "lt",
                        "lv", "mt", "ro", "sv", "da", "no"}
    if support == "european":
        return lang in {"en", "de", "es", "fr", "it", "pt", "nl", "pl", "ru", "uk",
                        "cs", "sk", "sl", "hr", "bg", "et", "fi", "el", "hu", "lt",
                        "lv", "mt", "ro", "sv", "da", "no"}
    return lang in {"en", "eng"}


def discover_asr_models(base_url: str, api_key: str, language: str | None = None) -> list[dict]:
    """Discover only models exposed by this configured NIM deployment."""
    base = base_url.rstrip("/")
    payload = {}
    for url in (_api_url(base, "/v1/models"), _api_url(base, "/v1/metadata")):
        try:
            data = _http_json(url, api_key)
            payload.update(data)
        except Exception:
            # Some NVCF invocation endpoints expose transcription but not inventory.
            continue
    ids = _model_ids(payload)
    candidates = []
    for model_id in ids:
        match = _family(model_id)
        if not match:
            continue
        family, meta = match
        if _supports_language(meta, language):
            candidates.append({"id": model_id, "family": family, "rank": meta["rank"]})
    candidates.sort(key=lambda item: item["rank"])
    # A dedicated ASR invocation URL may report the generic id "unknown". In that
    # case the deployment itself is the model selector; do not invent a model id.
    if not candidates and any(str(x).lower() == "unknown" for x in ids):
        candidates.append({"id": None, "family": "deployed-asr", "rank": 100})
    # If inventory endpoints are absent, the explicitly configured ASR URL is still
    # a valid candidate; the real transcription request is the capability probe.
    if not ids:
        candidates.append({"id": None, "family": "configured-asr-endpoint", "rank": 100})
    return candidates


def _to_wav(source: Path, target: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("NVIDIA Speech NIM accepts WAV/OPUS/FLAC. Install FFmpeg to prepare the downloaded audio.")
    result = subprocess.run(
        [ffmpeg, "-nostdin", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "pcm_s16le", str(target)],
        capture_output=True, text=True, timeout=900,
    )
    if result.returncode or not target.is_file():
        raise RuntimeError("Could not prepare audio for NVIDIA Speech NIM: " + result.stderr[-1000:])
    return target


def _multipart(url: str, api_key: str, audio: Path, language: str | None,
               model: str | None, translate_to: str | None = None) -> dict:
    max_mb = int(os.getenv("FBTRANSCRIPT_MAX_UPLOAD_MB", "24"))
    size_mb = audio.stat().st_size / (1024 * 1024)
    if size_mb > max_mb:
        raise RuntimeError(f"Audio is {size_mb:.1f} MB; NVIDIA upload limit is {max_mb} MB.")
    boundary = "----FBTranscriptNvidiaBoundary7MA4YWxkTrZu0gW"
    fields = {"response_format": "json"}
    if model:
        fields["model"] = model
    else:
        fields["language"] = language or "multi"
    if translate_to:
        fields["target_language"] = translate_to
    body = bytearray()
    for key, value in fields.items():
        body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n").encode())
    body.extend((f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode())
    body.extend(audio.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    path = "/v1/audio/translations" if translate_to else "/v1/audio/transcriptions"
    request = urllib.request.Request(_api_url(url.rstrip("/"), path), data=bytes(body), headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[-1200:]
        raise RuntimeError(f"NVIDIA Speech endpoint returned HTTP {exc.code}: {detail}") from exc
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"text": str(value)}
    except json.JSONDecodeError:
        return {"text": raw}


def transcribe_nvidia(url: str, language: str | None = None,
                      translate_to: str | None = None) -> Transcript:
    api_key = os.getenv("NVIDIA_API_KEY")
    endpoints = _endpoint_urls()
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY is not set.")
    if not endpoints:
        raise RuntimeError("Set FBTRANSCRIPT_NVIDIA_ASR_ENDPOINTS to one or more NVIDIA Speech NIM/NVCF ASR endpoint URLs.")
    errors = []
    with tempfile.TemporaryDirectory(prefix="fbtranscript-nvidia-") as tmp:
        root = Path(tmp)
        info = FacebookExtractor().download_audio(url, str(root / "source.%(ext)s"))
        source = next((p for p in root.iterdir() if p.is_file()), None)
        if source is None:
            raise RuntimeError("Facebook audio download produced no file for NVIDIA recognition.")
        wav = _to_wav(source, root / "audio-16khz-mono.wav")
        for base in endpoints:
            try:
                candidates = discover_asr_models(base, api_key, language)
                if not candidates:
                    raise RuntimeError("No compatible ASR model was discovered on this endpoint.")
                for candidate in candidates:
                    try:
                        result = _multipart(base, api_key, wav, language, candidate["id"])
                        transcript_text = str(result.get("text") or "").strip()
                        if not transcript_text:
                            raise RuntimeError("NVIDIA endpoint returned an empty transcript.")
                        duration = float(info.get("duration") or 0)
                        segments = [Segment(start=0.0, duration=duration, text=transcript_text)]
                        translated_text = None
                        warnings = [f"Recognition engine: NVIDIA Speech NIM ({candidate['family']})"]
                        if translate_to:
                            try:
                                translated = _multipart(base, api_key, wav, language, candidate["id"], translate_to)
                                translated_text = str(translated.get("text") or "").strip() or None
                                if not translated_text:
                                    warnings.append("NVIDIA translation returned an empty result.")
                            except Exception as translation_error:
                                warnings.append(f"NVIDIA translation unavailable: {type(translation_error).__name__}: {translation_error}")
                        return Transcript(
                            source_url=url, title=info.get("title"),
                            language=result.get("language") or language or "auto",
                            language_name=result.get("language") or language,
                            source=f"NVIDIA:{candidate['family']}:{candidate['id'] or 'deployed'}",
                            segments=segments, warnings=warnings,
                            translated_text=translated_text,
                            translation_language=translate_to if translated_text else None,
                        )
                    except Exception as exc:
                        errors.append(f"{base} [{candidate['id'] or candidate['family']}]: {type(exc).__name__}: {exc}")
            except Exception as exc:
                errors.append(f"{base}: {type(exc).__name__}: {exc}")
    raise RuntimeError("All configured NVIDIA ASR endpoints/models failed: " + " | ".join(errors))


# Keep the existing dispatcher import stable while replacing Groq/OpenAI completely.
def transcribe_hosted(url: str, language: str | None = None,
                      translate_to: str | None = None) -> Transcript:
    return transcribe_nvidia(url, language, translate_to)
