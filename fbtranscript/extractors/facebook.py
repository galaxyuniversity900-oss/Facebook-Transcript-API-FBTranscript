"""Captions-first Facebook extraction using yt-dlp."""
import os
import re
import tempfile
from pathlib import Path
import yt_dlp
from ..models import Segment, Transcript
from ..security import validate_facebook_url

def _seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

def parse_vtt(path: Path) -> list[Segment]:
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"((?:\d{2}:)?\d{2}:\d{2}\.\d{3})\s+-->\s+((?:\d{2}:)?\d{2}:\d{2}\.\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)", re.S)
    found = []
    for match in pattern.finditer(text):
        cue = re.sub(r"<[^>]+>", "", match.group(3))
        cue = " ".join(x.strip() for x in cue.splitlines() if x.strip())
        if cue and cue.upper() != "WEBVTT":
            start, end = _seconds(match.group(1)), _seconds(match.group(2))
            found.append(Segment(start=start, duration=max(0, end-start), text=cue))
    return found

class FacebookExtractor:
    def __init__(self, cookie_file: str | None = None):
        self.cookie_file = cookie_file or os.getenv("FBTRANSCRIPT_COOKIE_FILE")

    def _options(self, **extra):
        opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
        if self.cookie_file:
            opts["cookiefile"] = self.cookie_file
        opts.update(extra)
        return opts

    def captions(self, url: str, languages: list[str] | None = None) -> Transcript:
        url = validate_facebook_url(url)
        with tempfile.TemporaryDirectory(prefix="fbtranscript-") as tmp:
            opts = self._options(skip_download=True, writesubtitles=True, writeautomaticsub=True,
                subtitleslangs=languages or ["ar", "en", "all"], subtitlesformat="vtt/best",
                outtmpl=str(Path(tmp) / "%(id)s.%(ext)s"))
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            if not info:
                raise RuntimeError("Video metadata could not be retrieved.")
            for file in sorted(Path(tmp).glob("*.vtt")):
                segments = parse_vtt(file)
                if segments:
                    lang = file.name.rsplit(".", 2)[-2]
                    return Transcript(source_url=url, title=info.get("title"), language=lang,
                        source="facebook-captions", segments=segments)
            return Transcript(source_url=url, title=info.get("title"), source="none",
                warnings=["No downloadable caption track was found."])

    def download_audio(self, url: str, template: str):
        """Try independent yt-dlp format/extraction profiles before declaring failure."""
        url = validate_facebook_url(url)
        profiles = [
            {"format": "bestaudio/best"},
            {"format": "best"},
            {"format": "bestvideo*+bestaudio/best"},
        ]
        errors = []
        for index, profile in enumerate(profiles, 1):
            options = self._options(
                outtmpl=template,
                retries=3,
                fragment_retries=3,
                extractor_retries=2,
                file_access_retries=2,
                socket_timeout=30,
                **profile,
            )
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                if info:
                    info["_fbtranscript_extraction_profile"] = index
                    return info
                errors.append(f"profile {index}: no metadata returned")
            except Exception as exc:
                errors.append(f"profile {index}: {type(exc).__name__}: {exc}")
        raise RuntimeError("All Facebook audio extraction profiles failed: " + " | ".join(errors[-3:]))
