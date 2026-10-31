"""Captions-first transcription orchestration."""
from .security import validate_facebook_url
from .extractors.facebook import FacebookExtractor
from .engines.whisper import transcribe_audio

def transcribe(url: str, *, languages=None, whisper=True, model_size="small", language=None):
    url = validate_facebook_url(url)
    result = FacebookExtractor().captions(url, languages)
    if result.segments or not whisper:
        return result
    try:
        return transcribe_audio(url, model_size=model_size, language=language)
    except Exception as exc:
        result.warnings.append(f"Whisper fallback unavailable: {exc}")
        return result
