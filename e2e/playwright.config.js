// @ts-check
import { defineConfig } from '@playwright/test';

const frontendPort = Number(process.env.SHENLAB_E2E_FRONTEND_PORT || '5180');
const backendPort = Number(process.env.SHENLAB_E2E_BACKEND_PORT || '5090');
const apiBase = process.env.SHENLAB_E2E_API_BASE || `http://127.0.0.1:${backendPort}`;

process.env.SHENLAB_E2E_FRONTEND_PORT = String(frontendPort);
process.env.SHENLAB_E2E_BACKEND_PORT = String(backendPort);
process.env.SHENLAB_E2E_API_BASE = apiBase;

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  webServer: {
    command: 'bash e2e/scripts/start-stack.sh',
    url: `http://127.0.0.1:${frontendPort}`,
    timeout: 120_000,
    reuseExistingServer: false,
    cwd: '..',
    env: process.env,
  },
});
