# Audit Record: Vercel Production Frontend -> Public API Real Run

Date: 2026-02-11

## Scope

- Real (non-mock) AlphaFold-Multimer run
- Full production path:
  - Website: `https://shenlab-web.vercel.app/#tools`
  - Public API: `https://chandra-unintentional-matrilaterally.ngrok-free.dev`
  - Backend service: `alphafold-multimer-service` on port `5090`
  - ColabFold Docker real compute (`alphafold2_multimer_v3`)
- Input pair (real UniProt links):
  - Protein A: `https://www.uniprot.org/uniprotkb/A0A2R8Y7G1/entry`
  - Protein B: `https://www.uniprot.org/uniprotkb/P35625/entry`

## Code Versions

- Frontend (`shenlab-web`): commit `34fb631`
- Backend (`alphafold-multimer-service`): commit `bc85a6f`

## Production UI Automation Evidence

Automation opened production website, submitted pair, and waited for final completion.

Observed status sequence:

- `queued`
- `running (...)`
- `Done.`

Observed final UI fields:

- Job ID: `job_20260211_220807_3c960242`
- Primary score: `0.2160`
- Metrics:
  - `ipTM = 0.192`
  - `pTM = 0.312`
  - `pLDDT = 45.8`
  - `ranking_confidence = 0.2160`

## Backend Job Record

- `job_id`: `job_20260211_220807_3c960242`
- status: `succeeded`
- started: `2026-02-11T22:08:07.006519Z`
- finished: `2026-02-11T22:19:30.356040Z`

## Final Numeric Result (API)

- Primary score (`ranking_confidence`): **`0.216`**
- `ipTM`: `0.192`
- `pTM`: `0.312`
- `pLDDT`: `45.8`

Formula check:

- expected `0.8 * ipTM + 0.2 * pTM` = `0.21600000000000003`
- reported = `0.216`
- absolute delta = `2.7755575615628914e-17` (numerically consistent)

## Public Audit Endpoints

- Status:
  - `GET https://chandra-unintentional-matrilaterally.ngrok-free.dev/api/v1/jobs/job_20260211_220807_3c960242`
- Result:
  - `GET https://chandra-unintentional-matrilaterally.ngrok-free.dev/api/v1/jobs/job_20260211_220807_3c960242/result`
- Artifact links (from result payload):
  - `/api/v1/jobs/job_20260211_220807_3c960242/artifacts/log.txt`
  - `/api/v1/jobs/job_20260211_220807_3c960242/artifacts/docker.log.txt`
  - `/api/v1/jobs/job_20260211_220807_3c960242/artifacts/rank_001.pdb`
  - `/api/v1/jobs/job_20260211_220807_3c960242/artifacts/scores_rank_001.json`

## Notes

- Runtime warning text includes:
  - `warning: Linking two modules of different target triples ...`
- This warning did not affect completion or score extraction.
- `verification.chain_lengths_match=false` in this run path; score is still derived from rank-001 parsed `ipTM`/`pTM` and formula is internally consistent.
