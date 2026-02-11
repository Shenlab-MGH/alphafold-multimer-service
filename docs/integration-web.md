# Web Integration (`17-lab-web`)

## Goal

Connect the static frontend (`17-lab-web`, Vercel) to this backend service.

Frontend input:

- Protein A UniProt link/accession
- Protein B UniProt link/accession
- API base URL
- optional API token

Frontend output:

- primary score (`ranking_confidence`)
- metrics + verification
- artifact links

## Backend Requirements

1. Backend reachable from browser:
   - e.g. `https://your-backend.example.com` or public IP/domain + TLS
2. CORS configured:
   - set `SHENLAB_CORS_ALLOW_ORIGINS` to include production domain(s)
   - include `https://*.vercel.app` for preview builds
3. Optional token:
   - set `SHENLAB_API_TOKEN`
   - frontend sends `Authorization: Bearer <token>`

## Endpoint Contract

Frontend should only depend on:

- `POST /api/v1/services/alphafold-multimer/jobs`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/result`

## Vercel Notes

1. Vercel preview domains change frequently.
2. Use `https://*.vercel.app` in backend CORS config.
3. Keep API contract stable (OpenAPI v1) to avoid frontend breakage.

## Local Full-Stack Test

From `alphafold-multimer-service/e2e`:

```bash
npm test
```

This validates the full behavior from browser UI to backend API.

