# Testing Guide

## Test Layers

1. Unit tests:
   - parser logic
   - UniProt parsing
   - metric calculation helpers
2. API/integration tests:
   - submit/status/result/artifact behavior
   - auth and validation errors
3. Contract test:
   - running app OpenAPI paths/methods match committed OpenAPI file
4. E2E browser tests:
   - frontend form -> backend job -> rendered results

## Run Backend Test Suite

```bash
cd alphafold-multimer-service
python -m pytest -q
```

## Run Front-to-Back E2E

```bash
cd alphafold-multimer-service/e2e
npm test
```

The e2e runner starts:

- backend mock service on `127.0.0.1:5090`
- frontend static server from `../shenlab-web` on `127.0.0.1:5180` (fallback: `../17-lab-web`)

You can override frontend path with:

```bash
export SHENLAB_FRONTEND_DIR=/absolute/path/to/shenlab-web
```

You can also override test ports and API base:

```bash
export SHENLAB_E2E_BACKEND_PORT=5091
export SHENLAB_E2E_FRONTEND_PORT=5181
export SHENLAB_E2E_API_BASE=http://127.0.0.1:5091
npm test
```

## Optional Real GPU Smoke Test

Use real mode by running backend without `SHENLAB_MOCK=1`, then submit a short `preset=fast` job and verify:

- status reaches `succeeded`
- result has `primary_score.value`
- artifacts are downloadable

## Real Full BDD (No Mock)

Run the browser test in real mode end-to-end (website input + real backend compute):

```bash
cd alphafold-multimer-service/e2e
SHENLAB_E2E_MODE=real \
SHENLAB_E2E_BACKEND_PORT=5100 \
SHENLAB_E2E_FRONTEND_PORT=5190 \
SHENLAB_E2E_API_BASE=http://127.0.0.1:5100 \
SHENLAB_DATA_DIR=/home/robot/workspace/shenlab/alphafold-multimer-service/data \
SHENLAB_COLABFOLD_CACHE_DIR=/home/robot/workspace/shenlab/alphafold-multimer-service/data/colabfold_cache \
SHENLAB_E2E_REAL_PROTEIN_A=A0A2R8Y7G1 \
SHENLAB_E2E_REAL_PROTEIN_B=P35625 \
npx playwright test tests/alphafold-multimer-real.spec.js --reporter=list
```

This validates:

- frontend auth + form submit
- API job creation/status/result paths
- real ColabFold execution
- formula consistency: `ranking_confidence ~= 0.8*ipTM + 0.2*pTM`

## CI Recommendations

1. PR: run `pytest` + Playwright e2e (mock mode)
2. Nightly: run one real GPU smoke test (if GPU runner exists)
3. Block merge on:
   - contract drift
   - API regression
   - frontend behavior regression
