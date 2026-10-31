"""Local speech recognition using whisper.cpp on Android or faster-whisper elsewhere."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from ..extractors.facebook import FacebookExtractor, parse_vtt
from ..models import Segment, Transcript

def _transcribe_whisper_cpp(url: str, language: str | None) -> Transcript:
    binary = shutil.which(os.getenv("FBTRANSCRIPT_WHISPER_BIN", "whisper-cli"))
    model = Path(os.getenv("FBTRANSCRIPT_WHISPER_MODEL", str(Path.home() / ".cache" / "fbtranscript" / "ggml-tiny.bin"))).expanduser()
    ffmpeg = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("Speech engine is not installed. Run: bash scripts/install-whisper-termux.sh")
    if not model.is_file():
        raise RuntimeError(f"Whisper model not found: {model}. Run scripts/install-whisper-termux.sh")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required. Install it with: pkg install ffmpeg")
    with tempfile.TemporaryDirectory(prefix="fbtranscript-audio-") as tmp:
        root = Path(tmp)
        info = FacebookExtractor().download_audio(url, str(root / "source.%(ext)s"))
        source = next((p for p in root.iterdir() if p.is_file()), None)
        if source is None:
            raise RuntimeError("Facebook audio download produced no file.")
        wav = root / "audio-16khz-mono.wav"
        converted = subprocess.run([ffmpeg, "-nostdin", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True, timeout=900)
        if converted.returncode != 0 or not wav.is_file():
            raise RuntimeError("Could not convert downloaded audio: " + converted.stderr[-1200:])
        prefix = root / "transcript"
        command = [binary, "-m", str(model), "-f", str(wav), "-ovtt", "-of", str(prefix), "-t", os.getenv("FBTRANSCRIPT_WHISPER_THREADS", "2")]
        if language:
            command += ["-l", language]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=7200)
        if completed.returncode != 0:
            raise RuntimeError("whisper.cpp failed: " + completed.stderr[-1600:])
        vtt = prefix.with_suffix(".vtt")
        if not vtt.is_file():
            raise RuntimeError("whisper.cpp completed without producing a VTT transcript.")
        segments = parse_vtt(vtt)
        if not segments:
            raise RuntimeError("No speech was recognized in the video's audio.")
        return Transcript(source_url=url, title=info.get("title"), language=language or "und", source="whisper.cpp", segments=segments)

def transcribe_audio(url: str, model_size: str = "tiny", language: str | None = None) -> Transcript:
    if shutil.which(os.getenv("FBTRANSCRIPT_WHISPER_BIN", "whisper-cli")):
        return _transcribe_whisper_cpp(url, language)
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("No speech engine installed. On Termux run bash scripts/install-whisper-termux.sh; on desktop install the optional faster-whisper dependency.") from exc
    with tempfile.TemporaryDirectory(prefix="fbtranscript-audio-") as tmp:
        template = str(Path(tmp) / "audio.%(ext)s")
        info = FacebookExtractor().download_audio(url, template)
        audio = next((p for p in Path(tmp).iterdir() if p.is_file()), None)
        if audio is None:
            raise RuntimeError("Audio download produced no file.")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        chunks, meta = model.transcribe(str(audio), language=language, vad_filter=True)
        segments = [Segment(start=float(s.start), duration=max(0, float(s.end-s.start)), text=s.text.strip()) for s in chunks if s.text.strip()]
        if not segments:
            raise RuntimeError("No speech was recognized in the video's audio.")
        return Transcript(source_url=url, title=info.get("title"), language=meta.language or "und", language_name=meta.language, source=f"faster-whisper:{model_size}", segments=segments)
