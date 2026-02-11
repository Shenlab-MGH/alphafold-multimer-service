# API Manual

## Base

- Base URL: `http://<host>:5090`
- Version prefix: `/api/v1`

## Endpoints

1. `GET /api/v1/health`
2. `GET /api/v1/services`
3. `POST /api/v1/services/alphafold-multimer/jobs`
4. `GET /api/v1/jobs/{job_id}`
5. `GET /api/v1/jobs/{job_id}/result`
6. `GET /api/v1/jobs/{job_id}/artifacts/{artifact_name}`

## Submit Job

`POST /api/v1/services/alphafold-multimer/jobs`

Request:

```json
{
  "protein_a": { "uniprot": "P35625" },
  "protein_b": { "uniprot": "A0A2R8Y7G1" },
  "preset": "fast"
}
```

Response:

```json
{
  "job_id": "job_20260211_191945_87d8b128",
  "status": "queued",
  "status_url": "/api/v1/jobs/job_20260211_191945_87d8b128",
  "result_url": "/api/v1/jobs/job_20260211_191945_87d8b128/result"
}
```

## Status

`GET /api/v1/jobs/{job_id}`

Important fields:

- `status`: `queued|running|succeeded|failed`
- `progress.stage`, `progress.message`, optional `progress.percent`
- `error` (on failed jobs)

## Result

`GET /api/v1/jobs/{job_id}/result`

Important fields:

- `primary_score.name`: always `ranking_confidence`
- `primary_score.value`: the single headline number
- `metrics`: `iptm`, `ptm`, `ranking_confidence`, `plddt`, optional interface PAE metrics
- `verification`: chain length checks
- `artifacts`: downloadable files

## Primary Score Definition

`ranking_confidence = 0.8 * ipTM + 0.2 * pTM`

This is the multimer ranking metric used for headline reporting in the service.

## Errors

Typical response schema:

```json
{
  "error": "Validation error",
  "details": { "errors": [] }
}
```

Status codes:

- `401`: missing/invalid token
- `404`: unknown job/artifact
- `409`: result requested before success
- `422`: validation error

## Source of Truth

Use `openapi/alphafold-multimer-service.v1.openapi.yaml` for full schema and contract checks.

