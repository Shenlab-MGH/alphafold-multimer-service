from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    details: dict | None = None
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    time: datetime
    version: str | None = None


class ServiceInfo(BaseModel):
    name: str
    version: str
    description: str


class ServiceListResponse(BaseModel):
    services: list[ServiceInfo]


class ProteinRef(BaseModel):
    uniprot: str = Field(..., description="UniProt accession or UniProt URL (entry or FASTA).")


AlphaFoldMultimerPreset = Literal["fast", "full"]


class AlphaFoldMultimerJobOptions(BaseModel):
    num_recycles: int | None = Field(default=None, ge=0, le=30)


class AlphaFoldMultimerJobCreateRequest(BaseModel):
    protein_a: ProteinRef
    protein_b: ProteinRef
    preset: AlphaFoldMultimerPreset = "fast"
    options: AlphaFoldMultimerJobOptions | None = None


JobStatus = Literal["queued", "running", "succeeded", "failed"]


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    status_url: str
    result_url: str


class JobProgress(BaseModel):
    stage: str
    message: str
    percent: float | None = Field(default=None, ge=0, le=100)


class JobStatusResponse(BaseModel):
    job_id: str
    service: str
    status: JobStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    progress: JobProgress
    error: str | None = None


class PrimaryScore(BaseModel):
    name: Literal["ranking_confidence"]
    value: float


class Artifact(BaseModel):
    name: str
    url: str
    media_type: str | None = None
    size_bytes: int | None = None


class AlphaFoldMultimerMetrics(BaseModel):
    iptm: float
    ptm: float
    ranking_confidence: float
    plddt: float
    interface_pae_mean: float | None = None
    interface_pae_mean_ab: float | None = None
    interface_pae_mean_ba: float | None = None


class AlphaFoldMultimerVerification(BaseModel):
    chain_lengths_match: bool
    chain_a_length_a3m: int | None = None
    chain_b_length_a3m: int | None = None
    chain_a_length_pdb: int | None = None
    chain_b_length_pdb: int | None = None


class AlphaFoldMultimerResultResponse(BaseModel):
    job_id: str
    service: Literal["alphafold-multimer"] = "alphafold-multimer"
    status: JobStatus
    primary_score: PrimaryScore
    metrics: AlphaFoldMultimerMetrics
    verification: AlphaFoldMultimerVerification
    artifacts: list[Artifact]

