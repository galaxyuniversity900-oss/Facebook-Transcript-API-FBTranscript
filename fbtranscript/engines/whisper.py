"""Optional offline-capable faster-whisper fallback."""
import tempfile
from pathlib import Path
from ..extractors.facebook import FacebookExtractor
from ..models import Segment, Transcript

def transcribe_audio(url: str, model_size: str = "small", language: str | None = None) -> Transcript:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Install optional Whisper support: pip install '.[whisper]'") from exc
    with tempfile.TemporaryDirectory(prefix="fbtranscript-audio-") as tmp:
        template = str(Path(tmp) / "audio.%(ext)s")
        info = FacebookExtractor().download_audio(url, template)
        audio = next((p for p in Path(tmp).iterdir() if p.is_file()), None)
        if audio is None:
            raise RuntimeError("Audio download produced no file.")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        chunks, meta = model.transcribe(str(audio), language=language, vad_filter=True)
        segments = [Segment(start=float(s.start), duration=max(0, float(s.end-s.start)), text=s.text.strip())
                    for s in chunks if s.text.strip()]
        return Transcript(source_url=url, title=info.get("title"), language=meta.language or "und",
            language_name=meta.language, source=f"faster-whisper:{model_size}", segments=segments)
