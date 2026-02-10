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
cd shenlab-services
SHENLAB_MOCK=1 uvicorn shenlab_services.api:create_app --factory --host 0.0.0.0 --port 5090
```

## Run On GPU Server (Real)

Requirements:

- Docker + NVIDIA Container Toolkit installed and working (`docker run --gpus all ...`)
- ColabFold Docker image pulled (or it will be pulled automatically)
- Host `ptxas` available at `SHENLAB_HOST_PTXAS_PATH` for RTX 5090

Run:

```bash
cd shenlab-services
export SHENLAB_DATA_DIR=/data/shenlab-services
export SHENLAB_CORS_ALLOW_ORIGINS="https://*.vercel.app,https://YOUR-PROD-DOMAIN"
uvicorn shenlab_services.api:create_app --factory --host 0.0.0.0 --port 5090
```

## systemd (Example)

Create `/etc/systemd/system/shenlab-services.service`:

```ini
[Unit]
Description=Shen Lab Services API
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/home/robot/workspace/shenlab/shenlab-services
Environment=SHENLAB_DATA_DIR=/data/shenlab-services
Environment=SHENLAB_CORS_ALLOW_ORIGINS=https://*.vercel.app
# Environment=SHENLAB_API_TOKEN=... (optional)
ExecStart=/home/robot/miniconda3/bin/uvicorn shenlab_services.api:create_app --factory --host 0.0.0.0 --port 5090
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now shenlab-services
sudo systemctl status shenlab-services
```

