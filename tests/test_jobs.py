from fbtranscript.jobs import JobStore

def test_job_lifecycle_and_persistence(tmp_path):
    path = str(tmp_path / "jobs.sqlite3")
    store = JobStore(path)
    created = store.create({"url": "https://www.facebook.com/watch/?v=1"})
    assert created["status"] == "queued"
    store.update(created["id"], "running")
    store.update(created["id"], "completed", result={"text": "hello"})
    reopened = JobStore(path)
    found = reopened.get(created["id"])
    assert found["status"] == "completed"
    assert found["result"] == {"text": "hello"}

def test_interrupted_jobs_are_recoverable(tmp_path):
    store = JobStore(str(tmp_path / "jobs.sqlite3"))
    job = store.create({"url": "https://www.facebook.com/watch/?v=1"})
    store.update(job["id"], "running")
    store.recover_interrupted()
    found = store.get(job["id"])
    assert found["status"] == "failed"
    assert "retry" in found["error"]
