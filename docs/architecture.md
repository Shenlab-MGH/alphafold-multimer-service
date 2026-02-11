# Architecture

## Overview

The service has three runtime layers:

1. HTTP API (`FastAPI`)
2. Job manager + queue (`JobManager`, single worker thread)
3. Runner (`MockAlphaFoldMultimerRunner` or `ColabFoldDockerRunner`)

The API is asynchronous from the client perspective:

- Client submits a job.
- Backend returns `job_id`.
- Client polls status.
- Client fetches result after success.

## Core Flow

1. `POST /api/v1/services/alphafold-multimer/jobs`
2. Request is validated and saved as `jobs/<job_id>/job.json`
3. Job enters queue (`queued` -> `running`)
4. Runner executes:
   - Parse UniProt IDs
   - Fetch FASTA
   - Build multimer input (`A:B`)
   - Run ColabFold (real mode) or fixture pipeline (mock mode)
   - Parse metrics and verification
5. Result is written to `jobs/<job_id>/result.json`
6. Status becomes `succeeded` or `failed`

## Data Layout

Within `SHENLAB_DATA_DIR`:

- `jobs/<job_id>/job.json`: request and status metadata
- `jobs/<job_id>/result.json`: API-facing result payload
- `jobs/<job_id>/artifacts/*`: logs and model outputs

## Concurrency Model

- Single in-process worker thread.
- FIFO queue, one heavy inference job at a time.
- Designed for one GPU server.

## Failure Model

Common failure points:

- Invalid UniProt references
- UniProt fetch failures (network/HTTP)
- Docker runtime errors
- ColabFold failures
- Output parsing failures

Failures are captured into job status:

- `status=failed`
- `error` string in job status

## Security/Access

- Optional Bearer token via `SHENLAB_API_TOKEN`
- CORS allow-list with regex support for Vercel preview domains
- Artifact download path traversal protection

