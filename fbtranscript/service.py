"""Audio-first speech transcription orchestration."""
from .security import validate_facebook_url
from .extractors.facebook import FacebookExtractor
from .engines.whisper import transcribe_audio


def transcribe(url: str, *, languages=None, whisper=True, model_size="tiny", language=None):
    """Transcribe spoken audio by default; captions are available only by explicit opt-out."""
    url = validate_facebook_url(url)
    if whisper:
        # Never silently substitute page captions for spoken words.
        return transcribe_audio(url, model_size=model_size, language=language)
    return FacebookExtractor().captions(url, languages)
