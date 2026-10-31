"""Command line entry point."""
import argparse
import sys
from pathlib import Path
from .service import transcribe
from .formatters import to_txt, to_json, to_srt, to_vtt, to_html

def main():
    p = argparse.ArgumentParser(prog="fbtranscript")
    p.add_argument("url")
    p.add_argument("-o", "--output")
    p.add_argument("-f", "--format", choices=["txt","json","srt","vtt","html"], default="txt")
    p.add_argument("--language")
    p.add_argument("--translate-to", choices=["en"], help="also translate the recognized speech to English")
    p.add_argument("--model", default="small")
    p.add_argument("--captions-only", action="store_true")
    p.add_argument("--caption-languages", default="ar,en,all")
    a = p.parse_args()
    try:
        result = transcribe(a.url, languages=[x.strip() for x in a.caption_languages.split(",")],
            whisper=not a.captions_only, model_size=a.model, language=a.language, translate_to=a.translate_to)
        output = {"txt":to_txt,"json":to_json,"srt":to_srt,"vtt":to_vtt,"html":to_html}[a.format](result)
        if a.output:
            Path(a.output).write_text(output, encoding="utf-8")
            print(f"Saved transcript to {a.output}", file=sys.stderr)
        else:
            print(output)
        if not result.segments:
            print("No transcript produced; inspect warnings with --format json.", file=sys.stderr)
    except Exception as exc:
        print(f"fbtranscript: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

if __name__ == "__main__":
    main()
