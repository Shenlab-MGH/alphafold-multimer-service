from __future__ import annotations

from pathlib import Path

import pytest

from shenlab_services.api import create_app
from shenlab_services.config import Settings


@pytest.fixture()
def app(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        api_token=None,
        mock_mode=True,
        cors_allow_origins=["http://localhost"],
        colabfold_image="ddhmed/colabfold:1.5.5-cuda12.2.2",
        colabfold_cache_dir=tmp_path / "cache",
        host_ptxas_path=None,
        default_preset="fast",
    )
    return create_app(settings)

