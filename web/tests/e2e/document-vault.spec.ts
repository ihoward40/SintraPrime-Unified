import { test, expect, request, type APIRequestContext } from '@playwright/test';
import { E2E_EMAIL, E2E_PASSWORD, E2E_TENANT_ID, authStorage, loginViaAPI } from './fixtures/auth';

test.describe.configure({ mode: 'serial' });

/**
 * End-to-end journey: Document Vault → Export Packet.
 *
 * 1. Seed test user (via global setup / manual pre-seeding).
 * 2. Login through real API to obtain JWT.
 * 3. Upload a test PDF via API so the vault has a real document.
 * 4. Navigate to /documents with the JWT in localStorage.
 * 5. Click "Export Packet" on the document.
 * 6. Verify the export result shows snapshot_id, packet_hash, audit_id, evidence_hash.
 */
test.describe('Document Vault export-packet journey', () => {
  let accessToken: string;
  let caseId: string;
  let documentId: string;

  test.beforeAll(async ({ baseURL }) => {
    // 1. Real login via API
    const login = await loginViaAPI(baseURL);
    expect(login.access_token).toBeTruthy();
    expect(login.user_id).toBeTruthy();
    accessToken = login.access_token;
    caseId = `e2e-case-${Date.now()}`;

    // 2. Upload a real document via API so we have something to export
    const apiCtx = await request.newContext({
      baseURL,
      extraHTTPHeaders: { Authorization: `Bearer ${accessToken}` },
    });
    try {
      const fileData = new Blob(['%PDF-1.4 fake pdf for e2e test'], { type: 'application/pdf' });
      const form = new FormData();
      // Browsers serialize Blob as binary; Playwright APIRequest needs explicit multipart helper.
      // Instead we use a small inline multipart boundary here.
      const boundary = '----E2EBoundary' + Date.now();
      const body = Buffer.concat([
        Buffer.from(
          `--${boundary}\r\n` +
            `Content-Disposition: form-data; name="file"; filename="e2e-test.pdf"\r\n` +
            `Content-Type: application/pdf\r\n\r\n`,
          'utf-8',
        ),
        Buffer.from(await fileData.arrayBuffer()),
        Buffer.from(`\r\n--${boundary}--\r\n`, 'utf-8'),
      ]);

      const uploadResponse = await apiCtx.post('/api/v1/documents/upload', {
        data: body,
        headers: {
          'Content-Type': `multipart/form-data; boundary=${boundary}`,
        },
      });
      if (!uploadResponse.ok()) {
        throw new Error(`Upload failed: ${uploadResponse.status()} ${await uploadResponse.text()}`);
      }
      const uploadJson = await uploadResponse.json();
      documentId = uploadJson.id;
      expect(documentId).toBeTruthy();
    } finally {
      await apiCtx.dispose();
    }
  });

  test('authenticated user sees documents and can export a packet', async ({ page, baseURL }) => {
    // 3. Seed localStorage with real JWT (frontend auth pattern)
    await page.context().addInitScript((token) => {
      localStorage.setItem('sintraprime_token', token);
    }, accessToken);

    // 4. Navigate to Document Vault
    await page.goto('http://localhost:3000/documents');

    // Wait for either real document list or the page title
    await expect(page.getByText('Document Vault')).toBeVisible();

    // The current DocumentVault.tsx falls back to mockDocuments if API fails.
    // For this test to be meaningful, we assert the real document appears.
    const realDoc = page.getByText('e2e-test.pdf', { exact: true });
    await expect(realDoc).toBeVisible({ timeout: 10_000 });

    // 5. Click the export button for this document row/card
    const exportButton = page.locator('button', { hasText: /Export Packet/i }).first();
    await expect(exportButton).toBeVisible();
    await exportButton.click();

    // 6. Verify the export result is displayed
    const result = page.locator('[data-testid="export-result"]');
    await expect(result).toBeVisible({ timeout: 15_000 });

    const snapshotId = page.locator('[data-testid="snapshot-id"]');
    const packetHash = page.locator('[data-testid="packet-hash"]');
    const auditId = page.locator('[data-testid="audit-id"]');

    await expect(snapshotId).not.toBeEmpty();
    await expect(packetHash).not.toBeEmpty();
    await expect(auditId).not.toBeEmpty();

    // ED-003: immutable evidence hash must differ from mutable packet hash
    const evidenceHash = page.locator('[data-testid="evidence-hash"]');
    await expect(evidenceHash).not.toBeEmpty();
    await expect(evidenceHash).not.toHaveText(await packetHash.textContent() || '');
  });
});
