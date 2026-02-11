# AlphaFold-Multimer Service

`alphafold-multimer-service` is a backend service that accepts two UniProt proteins and returns:

- Primary score: `ranking_confidence = 0.8*ipTM + 0.2*pTM`
- Detailed metrics: `ipTM`, `pTM`, `pLDDT`, interface PAE summary
- Verification: A3M and PDB chain length consistency
- Artifacts: log, PDB, PAE JSON, score JSON, input files

The service is designed for lab deployment on a GPU server and exposes a stable versioned API (`/api/v1/...`).

## Quick Start

### 1) Run backend in mock mode (no GPU)

```bash
cd alphafold-multimer-service
SHENLAB_MOCK=1 uvicorn alphafold_multimer_service.api:create_app --factory --host 0.0.0.0 --port 5090
```

### 2) Health check

```bash
curl -s http://127.0.0.1:5090/api/v1/health | jq
```

### 3) Submit one job

```bash
curl -s -X POST http://127.0.0.1:5090/api/v1/services/alphafold-multimer/jobs \
  -H 'Content-Type: application/json' \
  -d '{
    "protein_a": { "uniprot": "https://www.uniprot.org/uniprotkb/P35625/entry" },
    "protein_b": { "uniprot": "A0A2R8Y7G1" },
    "preset": "fast"
  }' | jq
```

Poll and fetch result:

```bash
curl -s http://127.0.0.1:5090/api/v1/jobs/<JOB_ID> | jq
curl -s http://127.0.0.1:5090/api/v1/jobs/<JOB_ID>/result | jq
```

## API Contract

- OpenAPI source of truth: `openapi/alphafold-multimer-service.v1.openapi.yaml`

Frontend clients should use this file as the integration contract.

## Documentation Map

- Service behavior/spec: `docs/specs/alphafold-multimer-pair.md`
- Pipeline details: `docs/alphafold-multimer-pair-service.md`
- Architecture: `docs/architecture.md`
- API manual: `docs/api.md`
- Deployment: `docs/deploy.md`
- Operations runbook: `docs/operations.md`
- Testing guide: `docs/testing.md`
- Web integration guide: `docs/integration-web.md`

## Repository Structure

- `alphafold_multimer_service/`: service code
- `openapi/`: API contract files
- `tests/`: unit/API/contract tests
- `e2e/`: front-to-back browser tests (Playwright)
- `docs/`: design, deployment, and operations manuals

## Production Notes

- Real inference uses ColabFold + AlphaFold2-Multimer v3 in Docker.
- RTX 5090 typically requires mounting host `ptxas`.
- Jobs are queued and executed one-at-a-time on a single GPU worker.
