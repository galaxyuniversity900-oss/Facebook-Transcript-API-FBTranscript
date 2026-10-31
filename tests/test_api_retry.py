from fastapi.testclient import TestClient
from fbtranscript import api
from fbtranscript.jobs import JobStore
from fbtranscript.models import Segment, Transcript

def test_failed_job_can_be_retried(monkeypatch, tmp_path):
    store = JobStore(str(tmp_path / "retry.sqlite3"))
    api.store = store
    job = store.create({"url":"https://www.facebook.com/watch/?v=123","whisper":False})
    store.update(job["id"], "failed", error="temporary error")
    def fake_transcribe(url, **kwargs):
        return Transcript(source_url=url, segments=[Segment(start=0,duration=1,text="retried")])
    monkeypatch.setattr(api, "transcribe", fake_transcribe)
    client = TestClient(api.app)
    response = client.post("/api/v1/jobs/" + job["id"] + "/retry")
    assert response.status_code == 202
    result = client.get("/api/v1/jobs/" + job["id"] + "/result")
    assert result.status_code == 200
    assert result.json()["segments"][0]["text"] == "retried"
