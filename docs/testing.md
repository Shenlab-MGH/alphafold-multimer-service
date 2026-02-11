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
- frontend static server from `../17-lab-web` on `127.0.0.1:5180`

You can override frontend path with:

```bash
export SHENLAB_FRONTEND_DIR=/absolute/path/to/17-lab-web
```

## Optional Real GPU Smoke Test

Use real mode by running backend without `SHENLAB_MOCK=1`, then submit a short `preset=fast` job and verify:

- status reaches `succeeded`
- result has `primary_score.value`
- artifacts are downloadable

## CI Recommendations

1. PR: run `pytest` + Playwright e2e (mock mode)
2. Nightly: run one real GPU smoke test (if GPU runner exists)
3. Block merge on:
   - contract drift
   - API regression
   - frontend behavior regression

