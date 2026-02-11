# Operations Runbook

## Service Control

If using `systemd`:

```bash
sudo systemctl status alphafold-multimer-service
sudo systemctl restart alphafold-multimer-service
sudo journalctl -u alphafold-multimer-service -f
```

## Health Monitoring

```bash
curl -s http://127.0.0.1:5090/api/v1/health
```

Expected:

- HTTP 200
- `{"status":"ok", ...}`

## Job Monitoring

1. Submit job
2. Poll `/api/v1/jobs/{job_id}`
3. On `failed`, inspect:
   - `error` field from status API
   - `jobs/<job_id>/artifacts/docker.log.txt`
   - `jobs/<job_id>/artifacts/log.txt`

## Common Failure Cases

1. `Invalid token`:
   - Ensure frontend/API caller sends `Authorization: Bearer <token>`
2. UniProt fetch failures:
   - Verify outbound network to `rest.uniprot.org`
3. Docker runtime failures:
   - Verify Docker daemon and NVIDIA runtime
4. RTX 5090 inference compile errors:
   - Verify `SHENLAB_HOST_PTXAS_PATH` points to executable host `ptxas`

## Data Retention / Cleanup

Job artifacts can be large. Recommended:

- Keep recent N days in `SHENLAB_DATA_DIR/jobs`
- Archive or remove old job directories regularly

Example cleanup (manual):

```bash
find /data/alphafold-multimer-service/jobs -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +
```

## Incident Response Checklist

1. Confirm health endpoint
2. Confirm GPU availability (`nvidia-smi`)
3. Run one mock mode smoke test
4. Run one real mode test job
5. Inspect logs and restore normal queue operation

