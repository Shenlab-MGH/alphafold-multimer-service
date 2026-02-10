// @ts-check
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL: 'http://127.0.0.1:5180',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  webServer: {
    command: 'bash e2e/scripts/start-stack.sh',
    url: 'http://127.0.0.1:5180',
    timeout: 120_000,
    reuseExistingServer: false,
    cwd: '..',
  },
});
