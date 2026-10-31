"""FastAPI REST service and web UI."""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import __version__
from .security import validate_facebook_url
from .service import transcribe
from .formatters import to_txt, to_json, to_srt, to_vtt, to_html

WEB = Path(__file__).parent / "web"
app = FastAPI(title="FBTranscript API", version=__version__,
    description="Transcribe Facebook videos you are authorized to access.")
app.mount("/static", StaticFiles(directory=WEB), name="static")

class TranscribeRequest(BaseModel):
    url: str = Field(min_length=8, max_length=4096)
    languages: list[str] = Field(default_factory=lambda: ["ar", "en", "all"])
    whisper: bool = True
    model_size: str = "small"
    language: str | None = None

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": __version__}

@app.post("/api/v1/transcribe")
def create_transcript(request: TranscribeRequest):
    try:
        validate_facebook_url(request.url)
        return transcribe(request.url, languages=request.languages, whisper=request.whisper,
            model_size=request.model_size, language=request.language).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/api/v1/export/{format_name}")
def export_transcript(format_name: str, request: TranscribeRequest):
    renderers = {"txt": (to_txt, "text/plain; charset=utf-8"),
        "json": (to_json, "application/json"), "srt": (to_srt, "application/x-subrip"),
        "vtt": (to_vtt, "text/vtt; charset=utf-8"), "html": (to_html, "text/html; charset=utf-8")}
    if format_name not in renderers:
        raise HTTPException(status_code=404, detail="Supported formats: txt, json, srt, vtt, html.")
    try:
        result = transcribe(request.url, languages=request.languages, whisper=request.whisper,
            model_size=request.model_size, language=request.language)
        renderer, media_type = renderers[format_name]
        return Response(renderer(result), media_type=media_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB / "index.html")
