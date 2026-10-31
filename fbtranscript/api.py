"""FastAPI REST service, persistent jobs, and browser UI."""
from pathlib import Path
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import __version__
from .security import validate_facebook_url
from .service import transcribe
from .jobs import JobStore
from .formatters import to_txt, to_json, to_srt, to_vtt, to_html

WEB = Path(__file__).parent / "web"
app = FastAPI(title="FBTranscript API", version=__version__,
    description="Transcribe Facebook videos you are authorized to access.")
app.mount("/static", StaticFiles(directory=WEB), name="static")
store = JobStore()

class TranscribeRequest(BaseModel):
    url: str = Field(min_length=8, max_length=4096)
    languages: list[str] = Field(default_factory=lambda: ["ar", "en", "all"])
    whisper: bool = True
    model_size: str = "small"
    language: str | None = None
    translate_to: str | None = None

class BatchRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=25)
    languages: list[str] = Field(default_factory=lambda: ["ar", "en", "all"])
    whisper: bool = True
    model_size: str = "small"
    language: str | None = None
    translate_to: str | None = None

def _execute_job(job_id: str):
    job = store.get(job_id)
    if not job:
        return
    store.update(job_id, "running")
    try:
        payload = job["payload"]
        result = transcribe(payload["url"], languages=payload.get("languages"),
            whisper=payload.get("whisper", True), model_size=payload.get("model_size", "small"),
            language=payload.get("language"), translate_to=payload.get("translate_to"))
        store.update(job_id, "completed", result=result.model_dump())
    except Exception as exc:
        store.update(job_id, "failed", error=str(exc))

@app.on_event("startup")
def recover_jobs():
    store.recover_interrupted()

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": __version__}

@app.post("/api/v1/transcribe")
def create_transcript(request: TranscribeRequest):
    try:
        validate_facebook_url(request.url)
        return transcribe(request.url, languages=request.languages, whisper=request.whisper,
            model_size=request.model_size, language=request.language, translate_to=request.translate_to).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/api/v1/jobs", status_code=202)
def create_job(request: TranscribeRequest, background_tasks: BackgroundTasks):
    try:
        validate_facebook_url(request.url)
        job = store.create(request.model_dump())
        background_tasks.add_task(_execute_job, job["id"])
        return job
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/api/v1/jobs/batch", status_code=202)
def create_batch(request: BatchRequest, background_tasks: BackgroundTasks):
    try:
        for url in request.urls:
            validate_facebook_url(url)
        jobs = []
        for url in request.urls:
            payload = request.model_dump()
            payload.pop("urls")
            payload["url"] = url
            job = store.create(payload)
            background_tasks.add_task(_execute_job, job["id"])
            jobs.append(job)
        return {"jobs": jobs, "count": len(jobs)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/api/v1/jobs")
def list_jobs(limit: int = 50):
    return {"jobs": store.list(limit)}

@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

@app.get("/api/v1/jobs/{job_id}/result")
def get_job_result(job_id: str):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job is not completed.")
    return job["result"]

@app.post("/api/v1/jobs/{job_id}/retry", status_code=202)
def retry_job(job_id: str, background_tasks: BackgroundTasks):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "failed":
        raise HTTPException(status_code=409, detail="Only failed jobs can be retried.")
    store.update(job_id, "queued")
    background_tasks.add_task(_execute_job, job_id)
    return store.get(job_id)

@app.post("/api/v1/export/{format_name}")
def export_transcript(format_name: str, request: TranscribeRequest):
    renderers = {"txt": (to_txt, "text/plain; charset=utf-8"),
        "json": (to_json, "application/json"), "srt": (to_srt, "application/x-subrip"),
        "vtt": (to_vtt, "text/vtt; charset=utf-8"), "html": (to_html, "text/html; charset=utf-8")}
    if format_name not in renderers:
        raise HTTPException(status_code=404, detail="Supported formats: txt, json, srt, vtt, html.")
    try:
        result = transcribe(request.url, languages=request.languages, whisper=request.whisper,
            model_size=request.model_size, language=request.language, translate_to=request.translate_to)
        renderer, media_type = renderers[format_name]
        return Response(renderer(result), media_type=media_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(WEB / "index.html")
