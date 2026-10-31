"""Persistent SQLite job history for long-running transcriptions."""
from __future__ import annotations
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

def _now():
    return datetime.now(timezone.utc).isoformat()

class JobStore:
    def __init__(self, database: str | None = None):
        configured = database or os.getenv("FBTRANSCRIPT_DB")
        self.path = Path(configured).expanduser() if configured else Path.home() / ".fbtranscript" / "jobs.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL,
                result TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=20000")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, payload: dict) -> dict:
        job_id = uuid4().hex
        now = _now()
        with self._connect() as db:
            db.execute("INSERT INTO jobs(id,status,payload,created_at,updated_at) VALUES(?,?,?,?,?)",
                (job_id, "queued", json.dumps(payload, ensure_ascii=False), now, now))
        return self.get(job_id)

    def get(self, job_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._decode(row) if row else None

    def list(self, limit: int = 50) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (min(max(limit, 1), 200),)).fetchall()
        return [self._decode(row) for row in rows]

    def update(self, job_id: str, status: str, result: dict | None = None, error: str | None = None):
        with self._connect() as db:
            db.execute("UPDATE jobs SET status=?, result=?, error=?, updated_at=? WHERE id=?",
                (status, json.dumps(result, ensure_ascii=False) if result is not None else None,
                 error, _now(), job_id))

    def recover_interrupted(self):
        with self._connect() as db:
            db.execute("UPDATE jobs SET status='failed', error='Process stopped before the job completed; retry this job.', updated_at=? WHERE status='running'",
                (_now(),))

    @staticmethod
    def _decode(row):
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        item["result"] = json.loads(item["result"]) if item["result"] else None
        return item
