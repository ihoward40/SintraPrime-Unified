import { test, expect } from '@playwright/test';

test('SP-MC3D-001 enters the governed 3D Command Town', async ({ page }) => {
  const mutatingRequests: string[] = [];
  page.on('request', (request) => {
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method())) {
      mutatingRequests.push(`${request.method()} ${request.url()}`);
    }
  });

  await page.goto('/mission-control/town');

  await expect(page.getByRole('heading', { name: 'SintraPrime Command Town' })).toBeVisible();
  const enter = page.getByRole('button', { name: /ENTER 3D/i });
  await expect(enter).toBeVisible();
  await enter.click();

  await expect(page.getByText('COMMAND TOWN 3D')).toBeVisible();
  await expect(page.getByText(/NO EXECUTION AUTHORITY/i)).toBeVisible();
  await expect(page.locator('.mc3d-renderer canvas')).toBeVisible();
  await expect(page.getByRole('button', { name: 'ENTER WORLD' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'EXIT 3D' })).toBeVisible();
  expect(mutatingRequests, 'visualization must not issue mutating network requests').toEqual([]);
});
