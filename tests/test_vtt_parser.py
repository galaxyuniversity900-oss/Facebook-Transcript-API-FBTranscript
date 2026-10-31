from fbtranscript.extractors.facebook import parse_vtt

def test_parse_webvtt_with_hours_and_arabic(tmp_path):
    path = tmp_path / "captions.vtt"
    path.write_text("WEBVTT\n\n00:00:01.250 --> 00:00:02.750\nمرحبا بالعالم\n", encoding="utf-8")
    parts = parse_vtt(path)
    assert len(parts) == 1
    assert parts[0].start == 1.25
    assert parts[0].duration == 1.5
    assert parts[0].text == "مرحبا بالعالم"

def test_parse_webvtt_without_hours(tmp_path):
    path = tmp_path / "captions.vtt"
    path.write_text("WEBVTT\n\n01:02.000 --> 01:04.000\nHello\n", encoding="utf-8")
    parts = parse_vtt(path)
    assert parts[0].start == 62
    assert parts[0].duration == 2
