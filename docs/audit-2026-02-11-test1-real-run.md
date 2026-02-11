# Audit Record: Real End-to-End Run (test1 pair)

Date: 2026-02-11

## Scope

- Real (non-mock) AlphaFold-Multimer run
- End-to-end path: website form -> backend API -> ColabFold Docker -> API result -> UI rendering
- Pair from `16-alphafold/test1`:
  - Protein A: `A0A2R8Y7G1`
  - Protein B: `P35625`

## Code Versions

- Frontend (`shenlab-web`): commit `9707068`
- Backend (`alphafold-multimer-service`): commit `80ebe44`

## Real BDD Command

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

Observed result: `1 passed (11.6m)`.

## Job and Runtime

- `job_id`: `job_20260211_204752_2cec466f`
- status: `succeeded`
- started: `2026-02-11T20:47:52.665576Z`
- finished: `2026-02-11T20:59:22.105408Z`

## Final Numeric Result

- Primary score (`ranking_confidence`): **`0.216`**
- `ipTM`: `0.192`
- `pTM`: `0.312`
- `pLDDT`: `45.8`

Formula check:

- expected `0.8 * ipTM + 0.2 * pTM` = `0.21600000000000003`
- reported = `0.216`
- absolute delta = `2.7755575615628914e-17` (numerically consistent)

## Artifacts (Audit Evidence)

Job directory:

- `data/jobs/job_20260211_204752_2cec466f/job.json`
- `data/jobs/job_20260211_204752_2cec466f/result.json`
- `data/jobs/job_20260211_204752_2cec466f/artifacts/log.txt`
- `data/jobs/job_20260211_204752_2cec466f/artifacts/docker.log.txt`
- `data/jobs/job_20260211_204752_2cec466f/artifacts/rank_001.pdb`
- `data/jobs/job_20260211_204752_2cec466f/artifacts/scores_rank_001.json`

Raw ColabFold outputs:

- `data/jobs/job_20260211_204752_2cec466f/work/out/log.txt`
- `data/jobs/job_20260211_204752_2cec466f/work/out/*rank_001*.pdb`
- `data/jobs/job_20260211_204752_2cec466f/work/out/*predicted_aligned_error_v1.json`

## Notes

- `verification.chain_lengths_match=false` because chain lengths were computed from PDB while A3M header parsing returned null in this run path.
- This does not change the primary score calculation. Ranking is derived from parsed rank-001 `ipTM` and `pTM`.
