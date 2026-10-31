from fbtranscript.formatters import to_json, to_srt, to_txt, to_vtt
from fbtranscript.models import Segment, Transcript

def sample():
 return Transcript(source_url="https://www.facebook.com/watch/?v=1", title="Sample",
  language="ar", source="test", segments=[Segment(start=1.25,duration=2,text="مرحبا بالعالم")])

def test_plain_text():
 t=sample()
 assert "مرحبا بالعالم" in to_txt(t)
 assert "[00:00:01.250]" in to_txt(t, timestamps=True)

def test_subtitle_formats():
 t=sample()
 assert "00:00:01,250 --> 00:00:03,250" in to_srt(t)
 assert "WEBVTT" in to_vtt(t)

def test_json_arabic():
 assert "مرحبا بالعالم" in to_json(sample())
