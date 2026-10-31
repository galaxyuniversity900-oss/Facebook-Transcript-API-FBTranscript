from fbtranscript.extractors import facebook


def test_audio_extractor_tries_next_profile_after_failure(monkeypatch, tmp_path):
    attempts = []

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options
            attempts.append(options["format"])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download):
            if len(attempts) == 1:
                raise RuntimeError("first format unavailable")
            return {"title": "Recovered video"}

    monkeypatch.setattr(facebook.yt_dlp, "YoutubeDL", FakeYoutubeDL)
    extractor = facebook.FacebookExtractor()
    info = extractor.download_audio(
        "https://www.facebook.com/watch/?v=123",
        str(tmp_path / "audio.%(ext)s"),
    )
    assert info["title"] == "Recovered video"
    assert info["_fbtranscript_extraction_profile"] == 2
    assert attempts[:2] == ["bestaudio/best", "best"]


def test_audio_extractor_reports_all_profile_failures(monkeypatch, tmp_path):
    class FakeYoutubeDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download):
            raise RuntimeError("blocked")

    monkeypatch.setattr(facebook.yt_dlp, "YoutubeDL", FakeYoutubeDL)
    extractor = facebook.FacebookExtractor()
    try:
        extractor.download_audio(
            "https://www.facebook.com/watch/?v=123",
            str(tmp_path / "audio.%(ext)s"),
        )
    except RuntimeError as exc:
        assert "All Facebook audio extraction profiles failed" in str(exc)
        assert "profile 3" in str(exc)
    else:
        raise AssertionError("Expected all extraction profiles to fail")

def test_recognition_dispatch_uses_configured_hosted_fallback(monkeypatch):
    import sys
    from types import ModuleType
    from fbtranscript.engines import whisper
    from fbtranscript.models import Segment, Transcript

    monkeypatch.setattr(whisper.shutil, "which", lambda name: None)
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    hosted = ModuleType("fbtranscript.engines.hosted")
    hosted.transcribe_hosted = lambda url, language, translate_to: Transcript(
        source_url=url,
        source="Groq:whisper-large-v3-turbo",
        segments=[Segment(start=0, duration=1, text="recognized")],
    )
    monkeypatch.setitem(sys.modules, "fbtranscript.engines.hosted", hosted)

    result = whisper.transcribe_audio("https://www.facebook.com/watch/?v=123")
    assert result.source.startswith("Groq:")
    assert result.text == "recognized"
    assert "faster-whisper: package is not installed" in result.warnings
