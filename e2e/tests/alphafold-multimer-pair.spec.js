import { test, expect } from '@playwright/test';

const ACCESS_HASH = '109d69efaeb106feec54886294ea328a962af4c6c40227dfa6859dd7332f6531';
const STORAGE_KEY = 'shenlab_auth';
const API_BASE = process.env.SHENLAB_E2E_API_BASE || 'http://127.0.0.1:5090';

test.describe('AlphaFold-Multimer (Pair) UI', () => {
  test('Given two UniProt refs, when run, then primary score is shown (mock)', async ({ page, request }) => {
    await test.step('Given I am authenticated in the frontend', async () => {
      await page.addInitScript(({ key, hash }) => {
        localStorage.setItem(key, hash);
      }, { key: STORAGE_KEY, hash: ACCESS_HASH });
    });

    await test.step('When I open the website and go to Tools', async () => {
      await page.goto('/');
      await page.getByTestId('nav-tools').click();
      await expect(page.getByTestId('af-form')).toBeVisible();
    });

    await test.step('And I submit Protein A + Protein B', async () => {
      await page.getByTestId('af-api-base').fill(API_BASE);
      await page.getByTestId('af-protein-a').fill('P35625');
      await page.getByTestId('af-protein-b').fill('A0A2R8Y7G1');
      await page.getByTestId('af-submit').click();
    });

    await test.step('Then the UI eventually shows a primary score number', async () => {
      await expect(page.getByTestId('af-primary-score')).toHaveText('0.3000');
      await expect(page.getByTestId('af-job-id')).not.toHaveText('-');
    });

    await test.step('And artifacts links resolve from the backend', async () => {
      const links = page.locator('[data-testid="af-artifacts"] a');
      await expect(links.first()).toBeVisible();
      const href = await links.first().getAttribute('href');
      expect(href).toContain(`${API_BASE}/api/v1/jobs/`);
      const resp = await request.get(href);
      expect(resp.ok()).toBeTruthy();
    });
  });

  test('Given an invalid UniProt ref, when run, then UI shows an error', async ({ page }) => {
    await page.addInitScript(({ key, hash }) => {
      localStorage.setItem(key, hash);
    }, { key: STORAGE_KEY, hash: ACCESS_HASH });

    await page.goto('/#tools');
    await expect(page.getByTestId('af-form')).toBeVisible();

    await page.getByTestId('af-api-base').fill(API_BASE);
    await page.getByTestId('af-protein-a').fill('not a url!!');
    await page.getByTestId('af-protein-b').fill('P35625');
    await page.getByTestId('af-submit').click();

    await expect(page.getByTestId('af-error')).toBeVisible();
    await expect(page.getByTestId('af-error')).toContainText('UniProt');
  });

  test('Given two real UniProt links, when run, then detailed result fields are rendered', async ({ page }) => {
    await page.addInitScript(({ key, hash }) => {
      localStorage.setItem(key, hash);
    }, { key: STORAGE_KEY, hash: ACCESS_HASH });

    await page.goto('/#tools');
    await expect(page.getByTestId('af-form')).toBeVisible();

    await page.getByTestId('af-api-base').fill(API_BASE);
    await page.getByTestId('af-protein-a').fill('https://www.uniprot.org/uniprotkb/P35625/entry');
    await page.getByTestId('af-protein-b').fill('https://rest.uniprot.org/uniprotkb/Q13424-1.fasta');
    await page.getByTestId('af-submit').click();

    await expect(page.getByTestId('af-status')).toHaveText('Done.');
    await expect(page.getByTestId('af-primary-score')).toHaveText('0.3000');
    await expect(page.getByTestId('af-metrics')).toContainText('ranking_confidence');
    await expect(page.getByTestId('af-verification')).toContainText('chain_lengths_match');
    await expect(page.locator('[data-testid="af-artifacts"] a').first()).toBeVisible();
  });
});
