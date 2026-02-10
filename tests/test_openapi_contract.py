from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient


def test_app_openapi_contains_documented_paths(app) -> None:
    client = TestClient(app)
    spec_path = Path(__file__).resolve().parents[1] / "openapi" / "shenlab-services.v1.openapi.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    documented_paths = spec["paths"].keys()

    app_openapi = client.get("/openapi.json").json()
    app_paths = app_openapi["paths"].keys()

    # Contract: every documented path exists in the running app.
    missing = [p for p in documented_paths if p not in app_paths]
    assert not missing, f"Missing paths in app OpenAPI: {missing}"

    # Contract: every documented method exists for the path.
    for path, doc_ops in spec["paths"].items():
        app_ops = app_openapi["paths"][path]
        for method in doc_ops.keys():
            assert method in app_ops, f"Missing {method.upper()} {path} in app OpenAPI"

