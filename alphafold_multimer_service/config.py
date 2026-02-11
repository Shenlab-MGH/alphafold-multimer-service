from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_token: str | None
    mock_mode: bool
    cors_allow_origins: list[str]

    colabfold_image: str
    colabfold_cache_dir: Path
    host_ptxas_path: Path | None

    default_preset: str


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("SHENLAB_DATA_DIR", "data")).resolve()
    api_token = os.environ.get("SHENLAB_API_TOKEN")
    mock_mode = _env_bool("SHENLAB_MOCK", False)

    cors_allow_origins_raw = os.environ.get(
        "SHENLAB_CORS_ALLOW_ORIGINS",
        "http://localhost,http://127.0.0.1,https://*.vercel.app",
    )
    cors_allow_origins = [s.strip() for s in cors_allow_origins_raw.split(",") if s.strip()]

    colabfold_image = os.environ.get("SHENLAB_COLABFOLD_IMAGE", "ddhmed/colabfold:1.5.5-cuda12.2.2")
    colabfold_cache_dir = Path(os.environ.get("SHENLAB_COLABFOLD_CACHE_DIR", str(data_dir / "colabfold_cache"))).resolve()

    host_ptxas_path_raw = os.environ.get("SHENLAB_HOST_PTXAS_PATH", "/usr/local/cuda-12.8/bin/ptxas")
    host_ptxas_path = Path(host_ptxas_path_raw).resolve() if host_ptxas_path_raw else None

    default_preset = os.environ.get("SHENLAB_AF_MULTIMER_PRESET", "fast").strip().lower() or "fast"

    return Settings(
        data_dir=data_dir,
        api_token=api_token,
        mock_mode=mock_mode,
        cors_allow_origins=cors_allow_origins,
        colabfold_image=colabfold_image,
        colabfold_cache_dir=colabfold_cache_dir,
        host_ptxas_path=host_ptxas_path,
        default_preset=default_preset,
    )

