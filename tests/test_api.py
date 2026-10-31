from fastapi.testclient import TestClient
from fbtranscript import api
from fbtranscript.jobs import JobStore
from fbtranscript.models import Segment, Transcript

def test_health_and_url_validation():
    client = TestClient(api.app)
    assert client.get("/api/v1/health").json()["status"] == "ok"
    response = client.post("/api/v1/transcribe", json={"url":"https://example.com/video"})
    assert response.status_code == 400

def test_background_job_api(monkeypatch, tmp_path):
    api.store = JobStore(str(tmp_path / "api-jobs.sqlite3"))
    def fake_transcribe(url, **kwargs):
        return Transcript(source_url=url, segments=[Segment(start=0,duration=1,text="hello")])
    monkeypatch.setattr(api, "transcribe", fake_transcribe)
    client = TestClient(api.app)
    response = client.post("/api/v1/jobs", json={"url":"https://www.facebook.com/watch/?v=123","whisper":False})
    assert response.status_code == 202
    job_id = response.json()["id"]
    detail = client.get("/api/v1/jobs/" + job_id).json()
    assert detail["status"] == "completed"
    assert client.get("/api/v1/jobs/" + job_id + "/result").json()["segments"][0]["text"] == "hello"
