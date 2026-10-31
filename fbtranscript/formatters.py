"""TXT, JSON, SRT, VTT and HTML serializers."""
import html
import json
from .models import Transcript

def stamp(seconds: float, comma: bool = False) -> str:
    ms = max(0, round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02}{',' if comma else '.'}{milli:03}"

def to_json(t: Transcript) -> str:
    return json.dumps(t.model_dump(), ensure_ascii=False, indent=2)

def to_txt(t: Transcript, timestamps: bool = False) -> str:
    if timestamps:
        return "\n".join(f"[{stamp(s.start)}] {s.text}" for s in t.segments) + "\n"
    original = t.text
    translated = (t.translated_text or "").strip()
    parts = [part for part in (original, ("[English translation]\n" + translated) if translated else "") if part]
    return "\n\n".join(parts) + ("\n" if parts else "")

def to_srt(t: Transcript) -> str:
    return "\n\n".join(f"{i}\n{stamp(s.start, True)} --> {stamp(s.end, True)}\n{s.text}" for i, s in enumerate(t.segments, 1))

def to_vtt(t: Transcript) -> str:
    return "WEBVTT\n\n" + "\n\n".join(f"{stamp(s.start)} --> {stamp(s.end)}\n{s.text}" for s in t.segments)

def to_html(t: Transcript) -> str:
    title = html.escape(t.title or "Transcript")
    rows = "".join(f"<li><time>{stamp(s.start)}</time> {html.escape(s.text)}</li>" for s in t.segments)
    return f"<!doctype html><html><meta charset=\"utf-8\"><title>{title}</title><h1>{title}</h1><ol>{rows}</ol></html>"
