from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from alphafold_multimer_service.api import create_app
from alphafold_multimer_service.config import Settings


def test_create_job_rejects_invalid_uniprot_ref(app) -> None:
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/services/alphafold-multimer/jobs",
            json={
                "protein_a": {"uniprot": "not a url!!"},
                "protein_b": {"uniprot": "P35625"},
                "preset": "fast",
            },
        )
        assert r.status_code == 422
        body = r.json()
        assert "error" in body


def test_create_job_requires_token_when_configured(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        api_token="secret-token",
        mock_mode=True,
        cors_allow_origins=["http://localhost"],
        colabfold_image="ddhmed/colabfold:1.5.5-cuda12.2.2",
        colabfold_cache_dir=tmp_path / "cache",
        host_ptxas_path=None,
        default_preset="fast",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        r = client.post(
            "/api/v1/services/alphafold-multimer/jobs",
            json={
                "protein_a": {"uniprot": "P35625"},
                "protein_b": {"uniprot": "A0A2R8Y7G1"},
                "preset": "fast",
            },
        )
        assert r.status_code == 401

        r2 = client.post(
            "/api/v1/services/alphafold-multimer/jobs",
            headers={"Authorization": "Bearer secret-token"},
            json={
                "protein_a": {"uniprot": "P35625"},
                "protein_b": {"uniprot": "A0A2R8Y7G1"},
                "preset": "fast",
            },
        )
        assert r2.status_code == 201

