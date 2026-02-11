# Web Integration (`shenlab-web`)

## Goal

Connect the static frontend (`shenlab-web`, Vercel) to this backend service.

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

## Tailscale-First Deployment Notes

If you want private network access first (before public cloud exposure):

1. Start backend on the node:
   - `uvicorn alphafold_multimer_service.api:create_app --factory --host 0.0.0.0 --port 5090`
2. Tailnet access URL (same tailnet users):
   - `http://robot-intel.taild54253.ts.net:5090`
3. For browser access from HTTPS frontend (Vercel), API must also be HTTPS:
   - use `tailscale funnel` or a public HTTPS ingress
4. One-time operator setup (requires root on host):
   - `sudo tailscale set --operator=$USER`
5. Then expose:
   - `tailscale funnel --bg --yes 5090`

If `tailscale funnel` returns `serve config denied`, your user is not an allowed operator yet.
In that case either:

- run the one-time `sudo tailscale set --operator=$USER`, or
- use another HTTPS tunnel first (for example `ngrok http 5090`) until ops grants Tailscale operator access.

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
