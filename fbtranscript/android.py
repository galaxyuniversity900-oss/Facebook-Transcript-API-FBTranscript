"""Android/Termux HTTP server using only Python's standard library."""
from __future__ import annotations

import json
import mimetypes
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__
from .formatters import to_html, to_json, to_srt, to_txt, to_vtt
from .jobs import JobStore
from .security import validate_facebook_url
from .service import transcribe

WEB = Path(__file__).parent / "web"
FORMATS = {
    "txt": (to_txt, "text/plain; charset=utf-8"),
    "json": (to_json, "application/json; charset=utf-8"),
    "srt": (to_srt, "application/x-subrip; charset=utf-8"),
    "vtt": (to_vtt, "text/vtt; charset=utf-8"),
    "html": (to_html, "text/html; charset=utf-8"),
}
STORE = JobStore()
POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fbtranscript")
LOCK = threading.Lock()


def _payload(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object.")
    languages = data.get("languages", ["ar", "en", "all"])
    if not isinstance(languages, list) or not all(isinstance(x, str) for x in languages):
        raise ValueError("languages must be a list of strings.")
    whisper = data.get("whisper", True)
    if not isinstance(whisper, bool):
        raise ValueError("whisper must be true or false.")
    return {
        "languages": languages,
        "whisper": whisper,
        "model_size": str(data.get("model_size", "tiny")),
        "language": data.get("language"),
        "translate_to": data.get("translate_to"),
    }


def _run_job(job_id: str) -> None:
    job = STORE.get(job_id)
    if not job:
        return
    STORE.update(job_id, "running")
    try:
        p = job["payload"]
        result = transcribe(p["url"], languages=p.get("languages"),
            whisper=p.get("whisper", True), model_size=p.get("model_size", "tiny"),
            language=p.get("language"), translate_to=p.get("translate_to"))
        STORE.update(job_id, "completed", result=result.model_dump())
    except Exception as exc:
        STORE.update(job_id, "failed", error=str(exc))


class Handler(BaseHTTPRequestHandler):
    server_version = "FBTranscript-Android/1"

    def log_message(self, fmt, *args):
        if os.getenv("FBTRANSCRIPT_ACCESS_LOG") == "1":
            super().log_message(fmt, *args)

    def _send(self, status: int, body, content_type="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else (
            body.encode("utf-8") if isinstance(body, str) else
            json.dumps(body, ensure_ascii=False).encode("utf-8"))
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length.") from exc
        if size < 1 or size > 1024 * 1024:
            raise ValueError("Request body must be between 1 byte and 1 MB.")
        data = json.loads(self.rfile.read(size).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object.")
        return data

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            return self._file("index.html", "text/html; charset=utf-8")
        if path == "/static/style.css":
            return self._file("style.css", "text/css; charset=utf-8")
        if path == "/static/script.js":
            return self._file("script.js", "application/javascript; charset=utf-8")
        if path == "/api/v1/health":
            return self._send(200, {"status": "ok", "version": __version__, "runtime": "android-stdlib"})
        if path == "/api/v1/jobs":
            limit = parse_qs(parsed.query).get("limit", ["30"])[0]
            try:
                return self._send(200, {"jobs": STORE.list(int(limit))})
            except ValueError:
                return self._send(400, {"detail": "limit must be an integer."})
        if path.startswith("/api/v1/jobs/"):
            tail = path.removeprefix("/api/v1/jobs/").strip("/")
            if tail.endswith("/result"):
                job_id = tail[:-7].strip("/")
                job = STORE.get(job_id)
                if not job:
                    return self._send(404, {"detail": "Job not found."})
                if job["status"] != "completed":
                    return self._send(409, {"detail": "Job is not completed."})
                return self._send(200, job["result"])
            job = STORE.get(tail)
            return self._send(200 if job else 404, job or {"detail": "Job not found."})
        return self._send(404, {"detail": "Not found."})

    def _file(self, name, content_type):
        try:
            return self._send(200, (WEB / name).read_bytes(), content_type)
        except OSError:
            return self._send(500, {"detail": "Web asset is missing."})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self._body()
            if path == "/api/v1/transcribe":
                common = _payload(data)
                url = validate_facebook_url(data.get("url", ""))
                result = transcribe(url, **common)
                return self._send(200, result.model_dump())
            if path == "/api/v1/jobs":
                common = _payload(data)
                url = validate_facebook_url(data.get("url", ""))
                job = STORE.create({**common, "url": url})
                POOL.submit(_run_job, job["id"])
                return self._send(202, job)
            if path == "/api/v1/jobs/batch":
                common = _payload(data)
                urls = data.get("urls")
                if not isinstance(urls, list) or not 1 <= len(urls) <= 25:
                    raise ValueError("urls must contain between 1 and 25 video URLs.")
                safe_urls = [validate_facebook_url(url) for url in urls]
                jobs = [STORE.create({**common, "url": url}) for url in safe_urls]
                for job in jobs:
                    POOL.submit(_run_job, job["id"])
                return self._send(202, {"jobs": jobs, "count": len(jobs)})
            if path.startswith("/api/v1/jobs/") and path.endswith("/retry"):
                job_id = path.removeprefix("/api/v1/jobs/").removesuffix("/retry").strip("/")
                job = STORE.get(job_id)
                if not job:
                    return self._send(404, {"detail": "Job not found."})
                if job["status"] != "failed":
                    return self._send(409, {"detail": "Only failed jobs can be retried."})
                STORE.update(job_id, "queued")
                POOL.submit(_run_job, job_id)
                return self._send(202, STORE.get(job_id))
            if path.startswith("/api/v1/export/"):
                fmt = path.rsplit("/", 1)[-1]
                if fmt not in FORMATS:
                    return self._send(404, {"detail": "Unsupported format."})
                common = _payload(data)
                url = validate_facebook_url(data.get("url", ""))
                result = transcribe(url, **common)
                render, mime = FORMATS[fmt]
                return self._send(200, render(result), mime)
            return self._send(404, {"detail": "Not found."})
        except (ValueError, json.JSONDecodeError) as exc:
            return self._send(400, {"detail": str(exc)})
        except Exception as exc:
            return self._send(422, {"detail": str(exc)})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.end_headers()


def main():
    host = os.getenv("FBTRANSCRIPT_HOST", "127.0.0.1")
    port = int(os.getenv("FBTRANSCRIPT_PORT", "8787"))
    STORE.recover_interrupted()
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    print(f"FBTranscript Android server: http://{host}:{port}", flush=True)
    print("Keep Termux open while using the app. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nStopping FBTranscript...", flush=True)
    finally:
        server.server_close()
        POOL.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
