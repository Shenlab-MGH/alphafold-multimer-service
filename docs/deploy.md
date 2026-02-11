# Deployment (Lab GPU Server)

This backend is meant to run on the lab machine with the GPU (RTX 5090) and expose HTTP on port `5090`.

## Environment Variables

- `SHENLAB_DATA_DIR`: where job outputs are stored (default: `./data`)
- `SHENLAB_API_TOKEN`: optional Bearer token; when set, job submission requires `Authorization: Bearer <token>`
- `SHENLAB_CORS_ALLOW_ORIGINS`: comma-separated allowed origins (default allows localhost + `*.vercel.app`)
- `SHENLAB_MOCK`: set `1` for mock mode (no GPU, deterministic outputs)

AlphaFold runner (ColabFold):

- `SHENLAB_COLABFOLD_IMAGE`: default `ddhmed/colabfold:1.5.5-cuda12.2.2`
- `SHENLAB_COLABFOLD_CACHE_DIR`: default `${SHENLAB_DATA_DIR}/colabfold_cache`
- `SHENLAB_HOST_PTXAS_PATH`: default `/usr/local/cuda-12.8/bin/ptxas` (RTX 5090 workaround)
- `SHENLAB_AF_MULTIMER_PRESET`: default `fast`

## Run Locally (Mock)

```bash
cd alphafold-multimer-service
SHENLAB_MOCK=1 uvicorn alphafold_multimer_service.api:create_app --factory --host 0.0.0.0 --port 5090
```

## Run On GPU Server (Real)

Requirements:

- Docker + NVIDIA Container Toolkit installed and working (`docker run --gpus all ...`)
- ColabFold Docker image pulled (or it will be pulled automatically)
- Host `ptxas` available at `SHENLAB_HOST_PTXAS_PATH` for RTX 5090

Run:

```bash
cd alphafold-multimer-service
export SHENLAB_DATA_DIR=/data/alphafold-multimer-service
export SHENLAB_CORS_ALLOW_ORIGINS="https://*.vercel.app,https://YOUR-PROD-DOMAIN"
uvicorn alphafold_multimer_service.api:create_app --factory --host 0.0.0.0 --port 5090
```

## systemd (Example)

Create `/etc/systemd/system/alphafold-multimer-service.service`:

```ini
[Unit]
Description=AlphaFold-Multimer Service API
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/robot/workspace/shenlab/alphafold-multimer-service
Environment=SHENLAB_DATA_DIR=/data/alphafold-multimer-service
Environment=SHENLAB_CORS_ALLOW_ORIGINS=https://*.vercel.app
# Environment=SHENLAB_API_TOKEN=... (optional)
ExecStart=/home/robot/miniconda3/bin/uvicorn alphafold_multimer_service.api:create_app --factory --host 0.0.0.0 --port 5090
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now alphafold-multimer-service
sudo systemctl status alphafold-multimer-service
```

