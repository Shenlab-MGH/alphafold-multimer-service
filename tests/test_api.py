from __future__ import annotations

import time

from fastapi.testclient import TestClient

from shenlab_services.alphafold_multimer.runner import AlphaFoldMultimerRunner


def test_health(app) -> None:
    with TestClient(app) as client:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "time" in body


def test_submit_and_get_result(app) -> None:
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/services/alphafold-multimer/jobs",
            json={
                "protein_a": {"uniprot": "P35625"},
                "protein_b": {"uniprot": "A0A2R8Y7G1"},
                "preset": "fast",
            },
        )
        assert r.status_code == 201
        job_id = r.json()["job_id"]

        # poll status until succeeded
        deadline = time.time() + 5
        status_obj = None
        while time.time() < deadline:
            s = client.get(f"/api/v1/jobs/{job_id}")
            assert s.status_code == 200
            status_obj = s.json()
            if status_obj["status"] == "succeeded":
                break
            time.sleep(0.05)
        assert status_obj is not None
        assert status_obj["status"] == "succeeded"

        res = client.get(f"/api/v1/jobs/{job_id}/result")
        assert res.status_code == 200
        obj = res.json()
        assert obj["job_id"] == job_id
        assert obj["service"] == "alphafold-multimer"
        assert obj["primary_score"]["name"] == "ranking_confidence"
        assert isinstance(obj["primary_score"]["value"], (int, float))
        assert isinstance(obj["metrics"]["ranking_confidence"], (int, float))
        assert obj["verification"]["chain_lengths_match"] is True
        assert obj["artifacts"]

        # Artifact download should work.
        first_art = obj["artifacts"][0]["name"]
        art = client.get(f"/api/v1/jobs/{job_id}/artifacts/{first_art}")
        assert art.status_code == 200


def test_unknown_job(app) -> None:
    with TestClient(app) as client:
        r = client.get("/api/v1/jobs/not-a-real-id")
        assert r.status_code == 404
        assert "error" in r.json()


def test_result_before_ready_returns_409(app) -> None:
    orig_runner = app.state.jobs._runner  # type: ignore[attr-defined]

    class SlowRunner(AlphaFoldMultimerRunner):
        def run_pair(self, **kwargs):
            time.sleep(0.2)
            # delegate to existing mock runner inside app
            return orig_runner.run_pair(**kwargs)

    # swap runner to slow down the worker
    app.state.jobs._runner = SlowRunner()  # type: ignore[attr-defined]

    with TestClient(app) as client:
        r = client.post(
            "/api/v1/services/alphafold-multimer/jobs",
            json={
                "protein_a": {"uniprot": "P35625"},
                "protein_b": {"uniprot": "A0A2R8Y7G1"},
                "preset": "fast",
            },
        )
        assert r.status_code == 201
        job_id = r.json()["job_id"]

        # request result immediately: should be 409 (queued/running)
        res = client.get(f"/api/v1/jobs/{job_id}/result")
        assert res.status_code == 409
        assert "error" in res.json()
