# Shen Lab Services (Backend)

This repository hosts **lab-deployed backend services** (GPU/CPU) behind a stable, versioned HTTP API.

Current service(s):

- **AlphaFold-Multimer (pair)**: submit 2 UniProt links/accessions, run prediction, and return a single **primary score** (`ranking_confidence`) plus detailed metrics and verification.

## Quick Start (Dev)

```bash
cd shenlab-services

# Mock mode (no GPU, deterministic results) on http://127.0.0.1:5090
SHENLAB_MOCK=1 uvicorn shenlab_services.api:create_app --factory --host 0.0.0.0 --port 5090
```

Health check:

```bash
curl -s http://127.0.0.1:5090/api/v1/health | jq
```

## Run A Job (Example)

```bash
curl -s -X POST http://127.0.0.1:5090/api/v1/services/alphafold-multimer/jobs \\
  -H 'Content-Type: application/json' \\
  -d '{
    "protein_a": { "uniprot": "https://www.uniprot.org/uniprotkb/P35625/entry" },
    "protein_b": { "uniprot": "A0A2R8Y7G1" },
    "preset": "fast"
  }' | jq
```

Then poll:

```bash
curl -s http://127.0.0.1:5090/api/v1/jobs/<JOB_ID> | jq
curl -s http://127.0.0.1:5090/api/v1/jobs/<JOB_ID>/result | jq
```

## API Definition (Source Of Truth)

OpenAPI spec:

- `openapi/shenlab-services.v1.openapi.yaml`

Frontend(s) (Vercel/static) should treat the OpenAPI file as the contract.

## Notes For Production

- The real AlphaFold-Multimer runner uses **ColabFold** to run AlphaFold2-Multimer models in Docker.
- For RTX 5090 (SM 12.0), the container CUDA toolchain may be too old; the runner supports bind-mounting host `ptxas`.
- A single-GPU job queue is used by default (one heavy job at a time).

