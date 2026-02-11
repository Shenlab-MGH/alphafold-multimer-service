from __future__ import annotations

import time

from fastapi.testclient import TestClient

from alphafold_multimer_service.alphafold_multimer.runner import AlphaFoldMultimerRunner


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


def test_list_jobs_history_includes_input_and_score(app) -> None:
    with TestClient(app) as client:
        created_ids: list[str] = []
        for protein_a, protein_b in [("P35625", "A0A2R8Y7G1"), ("A0A2R8Y7G1", "P35625")]:
            r = client.post(
                "/api/v1/services/alphafold-multimer/jobs",
                json={
                    "protein_a": {"uniprot": protein_a},
                    "protein_b": {"uniprot": protein_b},
                    "preset": "fast",
                },
            )
            assert r.status_code == 201
            created_ids.append(r.json()["job_id"])

        # wait until both jobs finish in mock mode
        deadline = time.time() + 10
        while time.time() < deadline:
            statuses = [client.get(f"/api/v1/jobs/{jid}").json()["status"] for jid in created_ids]
            if all(s == "succeeded" for s in statuses):
                break
            time.sleep(0.05)

        hist = client.get("/api/v1/jobs?limit=20&offset=0")
        assert hist.status_code == 200
        body = hist.json()
        assert body["total"] >= 2
        assert body["limit"] == 20
        assert body["offset"] == 0
        assert isinstance(body["jobs"], list)

        by_id = {row["job_id"]: row for row in body["jobs"]}
        for jid in created_ids:
            assert jid in by_id
            row = by_id[jid]
            assert row["status"] == "succeeded"
            assert row["service"] == "alphafold-multimer"
            assert row["protein_a_uniprot"] in {"P35625", "A0A2R8Y7G1"}
            assert row["protein_b_uniprot"] in {"P35625", "A0A2R8Y7G1"}
            assert row["preset"] == "fast"
            assert isinstance(row["primary_score_value"], (int, float))
            assert row["status_url"].endswith(f"/api/v1/jobs/{jid}")
            assert row["result_url"].endswith(f"/api/v1/jobs/{jid}/result")
