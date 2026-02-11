from __future__ import annotations

from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError

from alphafold_multimer_service import __version__
from alphafold_multimer_service.alphafold_multimer.runner import ColabFoldDockerRunner, MockAlphaFoldMultimerRunner
from alphafold_multimer_service.config import Settings, load_settings
from alphafold_multimer_service.jobs import JobManager, JobStore
from alphafold_multimer_service.schemas import (
    AlphaFoldMultimerJobCreateRequest,
    AlphaFoldMultimerResultResponse,
    ErrorResponse,
    HealthResponse,
    JobCreateResponse,
    JobListItem,
    JobListResponse,
    JobStatusResponse,
    ServiceInfo,
    ServiceListResponse,
)
from alphafold_multimer_service.uniprot import extract_uniprot_id


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _build_cors(app: FastAPI, settings: Settings) -> None:
    allow_origins: list[str] = []
    regex_parts: list[str] = []
    for origin in settings.cors_allow_origins:
        if origin == "https://*.vercel.app":
            # allow any Vercel preview domain (https://<name>.vercel.app)
            regex_parts.append(r"https://.*\.vercel\.app")
            continue

        # Allow local dev servers on any port when base host is listed.
        if origin in {"http://localhost", "http://127.0.0.1"}:
            regex_parts.append(re.escape(origin) + r"(?::\d+)?")
            continue

        allow_origins.append(origin)

    kwargs = dict(
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if regex_parts:
        # CORSMiddleware doesn't support wildcard origin lists; use a single union regex.
        origin_regex = "^(" + "|".join(regex_parts) + ")$"
        app.add_middleware(CORSMiddleware, allow_origins=allow_origins, allow_origin_regex=origin_regex, **kwargs)
        return

    app.add_middleware(CORSMiddleware, allow_origins=allow_origins, **kwargs)


def _require_bearer_if_configured(
    settings: Settings,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not settings.api_token:
        return
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    m = re.match(r"^Bearer\s+(.+)$", authorization.strip())
    if not m or m.group(1) != settings.api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    app = FastAPI(title="AlphaFold-Multimer Service API", version=__version__)
    _build_cors(app, settings)

    @app.exception_handler(HTTPException)
    def _http_exception_handler(_req: Request, exc: HTTPException) -> JSONResponse:
        # Ensure errors match the documented ErrorResponse schema.
        detail = exc.detail
        if isinstance(detail, dict):
            msg = detail.get("error") or detail.get("detail") or "Request failed"
            return JSONResponse(status_code=exc.status_code, content={"error": msg, "details": detail})
        return JSONResponse(status_code=exc.status_code, content={"error": str(detail)})

    @app.exception_handler(RequestValidationError)
    def _validation_exception_handler(_req: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Validation error", "details": {"errors": exc.errors()}},
        )

    store = JobStore(settings.data_dir)
    if settings.mock_mode:
        runner = MockAlphaFoldMultimerRunner()
    else:
        runner = ColabFoldDockerRunner(
            colabfold_image=settings.colabfold_image,
            colabfold_cache_dir=settings.colabfold_cache_dir,
            host_ptxas_path=settings.host_ptxas_path,
        )
    manager = JobManager(store=store, runner=runner)
    app.state.settings = settings
    app.state.jobs = manager

    @app.on_event("startup")
    def _startup() -> None:
        manager.start()

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(time=_utc_now(), version=__version__)

    @app.get("/api/v1/services", response_model=ServiceListResponse)
    def services() -> ServiceListResponse:
        return ServiceListResponse(
            services=[
                ServiceInfo(
                    name="alphafold-multimer",
                    version="v1",
                    description="AlphaFold2-Multimer scoring for a protein pair (UniProt -> metrics + artifacts).",
                )
            ]
        )

    @app.post(
        "/api/v1/services/alphafold-multimer/jobs",
        response_model=JobCreateResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            401: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    def create_job(
        req: AlphaFoldMultimerJobCreateRequest,
        _auth: None = Depends(lambda authorization=Header(default=None): _require_bearer_if_configured(settings, authorization)),
    ) -> JobCreateResponse:
        # FastAPI handles schema validation; we add a small guard for obviously-wrong refs.
        protein_a = req.protein_a.uniprot.strip()
        protein_b = req.protein_b.uniprot.strip()
        try:
            extract_uniprot_id(protein_a)
            extract_uniprot_id(protein_b)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        rec = manager.submit_alphafold_multimer(
            protein_a_ref=protein_a,
            protein_b_ref=protein_b,
            preset=req.preset or settings.default_preset,
            options=(req.options.model_dump() if req.options else None),
        )
        return JobCreateResponse(
            job_id=rec.job_id,
            status=rec.status,  # type: ignore[arg-type]
            status_url=f"/api/v1/jobs/{rec.job_id}",
            result_url=f"/api/v1/jobs/{rec.job_id}/result",
        )

    @app.get(
        "/api/v1/jobs",
        response_model=JobListResponse,
    )
    def list_jobs(
        limit: int = Query(default=20, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ) -> JobListResponse:
        rows = store.list(limit=limit, offset=offset)
        items: list[JobListItem] = []
        for rec in rows:
            req = rec.request or {}
            protein_a = (req.get("protein_a") or {}).get("uniprot")
            protein_b = (req.get("protein_b") or {}).get("uniprot")
            preset = req.get("preset")

            primary_score_value: float | None = None
            if rec.status == "succeeded":
                obj = store.read_result(rec.job_id)
                if obj is not None:
                    try:
                        primary_score_value = float((obj.get("primary_score") or {}).get("value"))
                    except (TypeError, ValueError):
                        primary_score_value = None

            items.append(
                JobListItem(
                    job_id=rec.job_id,
                    service=rec.service,
                    status=rec.status,  # type: ignore[arg-type]
                    created_at=rec.created_at,
                    started_at=rec.started_at,
                    finished_at=rec.finished_at,
                    protein_a_uniprot=protein_a,
                    protein_b_uniprot=protein_b,
                    preset=preset,
                    primary_score_value=primary_score_value,
                    status_url=f"/api/v1/jobs/{rec.job_id}",
                    result_url=f"/api/v1/jobs/{rec.job_id}/result",
                    error=rec.error,
                )
            )

        return JobListResponse(total=store.count(), limit=limit, offset=offset, jobs=items)

    @app.get(
        "/api/v1/jobs/{job_id}",
        response_model=JobStatusResponse,
        responses={404: {"model": ErrorResponse}},
    )
    def get_job(job_id: str) -> JobStatusResponse:
        rec = store.get(job_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Job not found")
        prog = rec.progress or {"stage": "unknown", "message": ""}
        return JobStatusResponse(
            job_id=rec.job_id,
            service=rec.service,
            status=rec.status,  # type: ignore[arg-type]
            created_at=rec.created_at,
            started_at=rec.started_at,
            finished_at=rec.finished_at,
            progress=prog,  # type: ignore[arg-type]
            error=rec.error,
        )

    @app.get(
        "/api/v1/jobs/{job_id}/result",
        response_model=AlphaFoldMultimerResultResponse,
        responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
    )
    def get_result(job_id: str) -> AlphaFoldMultimerResultResponse:
        rec = store.get(job_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if rec.status != "succeeded":
            raise HTTPException(status_code=409, detail=f"Job not finished (status={rec.status})")
        obj = store.read_result(job_id)
        if obj is None:
            raise HTTPException(status_code=409, detail="Result not ready")
        return AlphaFoldMultimerResultResponse.model_validate(obj)

    @app.get(
        "/api/v1/jobs/{job_id}/artifacts/{artifact_name}",
        responses={404: {"model": ErrorResponse}},
    )
    def get_artifact(job_id: str, artifact_name: str) -> Response:
        if "/" in artifact_name or "\\" in artifact_name or artifact_name.startswith("."):
            raise HTTPException(status_code=404, detail="Artifact not found")
        rec = store.get(job_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Job not found")

        artifacts_dir = store.job_dir(job_id) / "artifacts"
        path = (artifacts_dir / artifact_name).resolve()
        if not str(path).startswith(str(artifacts_dir.resolve())) or not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Artifact not found")
        return FileResponse(path)

    return app
