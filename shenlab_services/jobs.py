from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import threading
from typing import Any, Callable
import uuid

from pydantic import BaseModel, Field

from shenlab_services.alphafold_multimer.runner import AlphaFoldMultimerRunner


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class JobRecord(BaseModel):
    job_id: str
    service: str
    status: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: dict = Field(default_factory=lambda: {"stage": "queued", "message": "Queued", "percent": 0})
    error: str | None = None
    request: dict[str, Any]

    class Config:
        arbitrary_types_allowed = True


class JobStore:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._jobs_dir = data_dir / "jobs"
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._mem: dict[str, JobRecord] = {}

    @property
    def jobs_dir(self) -> Path:
        return self._jobs_dir

    def job_dir(self, job_id: str) -> Path:
        return self._jobs_dir / job_id

    def _job_json_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "job.json"

    def _result_json_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "result.json"

    def create_job(self, *, service: str, request: dict[str, Any]) -> JobRecord:
        job_id = f"job_{utc_now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        job_dir = self.job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=False)
        rec = JobRecord(
            job_id=job_id,
            service=service,
            status="queued",
            created_at=utc_now(),
            request=request,
        )
        self._mem[job_id] = rec
        self._write_job(rec)
        return rec

    def get(self, job_id: str) -> JobRecord | None:
        if job_id in self._mem:
            return self._mem[job_id]
        p = self._job_json_path(job_id)
        if not p.exists():
            return None
        obj = json.loads(p.read_text(encoding="utf-8"))
        rec = JobRecord.model_validate(obj)
        self._mem[job_id] = rec
        return rec

    def update(self, rec: JobRecord) -> None:
        self._mem[rec.job_id] = rec
        self._write_job(rec)

    def write_result(self, job_id: str, result: dict[str, Any]) -> None:
        p = self._result_json_path(job_id)
        p.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    def read_result(self, job_id: str) -> dict[str, Any] | None:
        p = self._result_json_path(job_id)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def _write_job(self, rec: JobRecord) -> None:
        p = self._job_json_path(rec.job_id)
        p.write_text(json.dumps(rec.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")


class JobManager:
    def __init__(self, *, store: JobStore, runner: AlphaFoldMultimerRunner) -> None:
        self._store = store
        self._runner = runner
        self._q: "queue.Queue[str]" = queue.Queue()
        self._worker = threading.Thread(target=self._loop, name="job-worker", daemon=True)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._worker.start()

    @property
    def store(self) -> JobStore:
        return self._store

    def submit_alphafold_multimer(
        self,
        *,
        protein_a_ref: str,
        protein_b_ref: str,
        preset: str,
        options: dict[str, Any] | None,
    ) -> JobRecord:
        rec = self._store.create_job(
            service="alphafold-multimer",
            request={
                "protein_a": {"uniprot": protein_a_ref},
                "protein_b": {"uniprot": protein_b_ref},
                "preset": preset,
                "options": options or {},
            },
        )
        self._q.put(rec.job_id)
        return rec

    def _loop(self) -> None:
        while True:
            job_id = self._q.get()
            try:
                self._run_one(job_id)
            except Exception as e:
                rec = self._store.get(job_id)
                if rec is not None:
                    rec = rec.model_copy(
                        update={
                            "status": "failed",
                            "finished_at": utc_now(),
                            "error": f"{type(e).__name__}: {e}",
                            "progress": {"stage": "failed", "message": "Failed", "percent": 100},
                        }
                    )
                    self._store.update(rec)
            finally:
                self._q.task_done()

    def _run_one(self, job_id: str) -> None:
        rec = self._store.get(job_id)
        if rec is None:
            return

        def progress_cb(stage: str, message: str, percent: float | None) -> None:
            nonlocal rec
            prog = {"stage": stage, "message": message}
            if percent is not None:
                prog["percent"] = float(percent)
            rec = rec.model_copy(update={"progress": prog})
            self._store.update(rec)

        rec = rec.model_copy(update={"status": "running", "started_at": utc_now()})
        self._store.update(rec)
        progress_cb("start", "Starting job", 0)

        req = rec.request
        options = req.get("options") or {}
        num_recycles_override = options.get("num_recycles")

        job_dir = self._store.job_dir(job_id)
        result = self._runner.run_pair(
            job_id=job_id,
            job_dir=job_dir,
            protein_a_ref=req["protein_a"]["uniprot"],
            protein_b_ref=req["protein_b"]["uniprot"],
            preset=req.get("preset") or "fast",
            num_recycles_override=num_recycles_override,
            progress_cb=progress_cb,
        )

        # Convert runner artifacts into API-facing artifact descriptors.
        api_artifacts: list[dict[str, Any]] = []
        for a in result.artifacts:
            name = a["name"]
            api_artifacts.append(
                {
                    "name": name,
                    "url": f"/api/v1/jobs/{job_id}/artifacts/{name}",
                    "media_type": a.get("media_type"),
                    "size_bytes": a.get("size_bytes"),
                }
            )

        api_result = {
            "job_id": job_id,
            "service": "alphafold-multimer",
            "status": "succeeded",
            "primary_score": {"name": "ranking_confidence", "value": float(result.metrics["ranking_confidence"])},
            "metrics": result.metrics,
            "verification": result.verification,
            "artifacts": api_artifacts,
        }
        self._store.write_result(job_id, api_result)

        rec = rec.model_copy(
            update={
                "status": "succeeded",
                "finished_at": utc_now(),
                "progress": {"stage": "done", "message": "Succeeded", "percent": 100},
            }
        )
        self._store.update(rec)

