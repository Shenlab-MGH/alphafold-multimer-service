import { test, expect } from '@playwright/test';

const ACCESS_HASH = '109d69efaeb106feec54886294ea328a962af4c6c40227dfa6859dd7332f6531';
const STORAGE_KEY = 'shenlab_auth';
const API_BASE = process.env.SHENLAB_E2E_API_BASE || 'http://127.0.0.1:5090';
const IS_REAL_MODE = process.env.SHENLAB_E2E_MODE === 'real';
const MAX_WAIT_MS = Number(process.env.SHENLAB_E2E_REAL_TIMEOUT_MS || '2400000'); // 40 min

const PROTEIN_A =
  process.env.SHENLAB_E2E_REAL_PROTEIN_A ||
  'https://www.uniprot.org/uniprotkb/P43220/entry';
const PROTEIN_B =
  process.env.SHENLAB_E2E_REAL_PROTEIN_B ||
  'https://www.uniprot.org/uniprotkb/P35625/entry';

test.describe('AlphaFold-Multimer Real BDD', () => {
  test('Given two real UniProt links, when submitted from UI, then final real result is returned and verified', async ({
    page,
    request,
  }) => {
    test.skip(!IS_REAL_MODE, 'Run only in real mode (SHENLAB_E2E_MODE=real)');
    test.setTimeout(MAX_WAIT_MS + 120000);

    await page.addInitScript(({ key, hash }) => {
      localStorage.setItem(key, hash);
    }, { key: STORAGE_KEY, hash: ACCESS_HASH });

    await page.goto('/#tools');
    await expect(page.getByTestId('af-form')).toBeVisible();

    await page.getByTestId('af-api-base').fill(API_BASE);
    await page.getByTestId('af-protein-a').fill(PROTEIN_A);
    await page.getByTestId('af-protein-b').fill(PROTEIN_B);
    await page.getByTestId('af-preset').selectOption('fast');
    await page.getByTestId('af-submit').click();

    await expect(page.getByTestId('af-job-id')).not.toHaveText('-');
    const jobId = ((await page.getByTestId('af-job-id').textContent()) || '').trim();
    expect(jobId).toMatch(/^job_/);

    const startMs = Date.now();
    let lastStatus = '';
    let apiSucceededAt = null;
    for (;;) {
      const errVisible = await page.getByTestId('af-error').isVisible().catch(() => false);
      if (errVisible) {
        const errText = await page.getByTestId('af-error').textContent();
        throw new Error(`UI returned error: ${errText || 'unknown'}`);
      }

      lastStatus = ((await page.getByTestId('af-status').textContent()) || '').trim();
      if (lastStatus === 'Done.') {
        break;
      }

      const apiStatusResp = await request.get(`${API_BASE}/api/v1/jobs/${encodeURIComponent(jobId)}`);
      expect(apiStatusResp.ok()).toBeTruthy();
      const apiStatusBody = await apiStatusResp.json();
      if (apiStatusBody.status === 'failed') {
        throw new Error(`Backend job failed: ${JSON.stringify(apiStatusBody)}`);
      }
      if (apiStatusBody.status === 'succeeded' && apiSucceededAt === null) {
        apiSucceededAt = Date.now();
      }
      if (apiSucceededAt !== null && Date.now() - apiSucceededAt > 30000) {
        throw new Error(`Backend succeeded but UI did not reach Done. Last UI status: ${lastStatus}`);
      }

      if (Date.now() - startMs > MAX_WAIT_MS) {
        throw new Error(`Timed out waiting for real run completion. Last status: ${lastStatus}`);
      }
      await page.waitForTimeout(5000);
    }

    const primaryUiText = ((await page.getByTestId('af-primary-score').textContent()) || '').trim();
    const primaryUi = Number(primaryUiText);
    expect(Number.isFinite(primaryUi)).toBeTruthy();
    expect(primaryUi).toBeGreaterThanOrEqual(0);
    expect(primaryUi).toBeLessThanOrEqual(1);

    await expect(page.getByTestId('af-metrics')).toContainText('ipTM');
    await expect(page.getByTestId('af-metrics')).toContainText('pTM');
    await expect(page.getByTestId('af-verification')).toContainText('chain_lengths_match');
    await expect(page.locator('[data-testid="af-artifacts"] a').first()).toBeVisible();

    const statusResp = await request.get(`${API_BASE}/api/v1/jobs/${encodeURIComponent(jobId)}`);
    expect(statusResp.ok()).toBeTruthy();
    const statusBody = await statusResp.json();
    expect(statusBody.status).toBe('succeeded');

    const resultResp = await request.get(`${API_BASE}/api/v1/jobs/${encodeURIComponent(jobId)}/result`);
    expect(resultResp.ok()).toBeTruthy();
    const resultBody = await resultResp.json();

    expect(resultBody.status).toBe('succeeded');
    expect(resultBody.job_id).toBe(jobId);
    expect(Array.isArray(resultBody.artifacts)).toBeTruthy();
    expect(resultBody.artifacts.length).toBeGreaterThanOrEqual(3);

    const iptm = Number(resultBody.metrics?.iptm);
    const ptm = Number(resultBody.metrics?.ptm);
    const ranking = Number(resultBody.primary_score?.value);
    expect(Number.isFinite(iptm)).toBeTruthy();
    expect(Number.isFinite(ptm)).toBeTruthy();
    expect(Number.isFinite(ranking)).toBeTruthy();

    // API defines ranking_confidence = 0.8 * ipTM + 0.2 * pTM
    const expectedRanking = 0.8 * iptm + 0.2 * ptm;
    expect(Math.abs(expectedRanking - ranking)).toBeLessThanOrEqual(1e-3);

    const plddt = Number(resultBody.metrics?.plddt);
    expect(Number.isFinite(plddt)).toBeTruthy();
    expect(plddt).toBeGreaterThanOrEqual(0);
    expect(plddt).toBeLessThanOrEqual(100);
  });
});
