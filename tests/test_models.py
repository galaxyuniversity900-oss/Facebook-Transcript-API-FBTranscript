from fbtranscript.models import Segment, Transcript

def test_text_and_duration():
 t=Transcript(source_url="https://www.facebook.com/watch/?v=1",
  segments=[Segment(start=0,duration=2.5,text="Hello")])
 assert t.text == "Hello"
 assert t.duration == 2.5
