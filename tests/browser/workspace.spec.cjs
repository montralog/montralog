const {test, expect} = require('@playwright/test');
const password = 'Browser-fixture-password-1';
async function signIn(page, username = 'admin') {
  await page.goto('/');
  await page.getByLabel('Username', {exact: true}).fill(username);
  await page.getByLabel('Password', {exact: true}).fill(password);
  await page.locator('#sign-in').click();
  await expect(page.locator('#login')).toBeHidden();
}

test('sign-in failures, profile persistence and logout use real browser sessions', async ({page}) => {
  await page.goto('/');
  await page.getByLabel('Username', {exact: true}).fill('admin');
  await page.getByLabel('Password', {exact: true}).fill('incorrect-password');
  await page.locator('#sign-in').click();
  await expect(page.locator('#login-notice')).toBeVisible();
  await page.getByLabel('Password', {exact: true}).fill(password);
  await page.locator('#sign-in').click();
  await expect(page.locator('#login')).toBeHidden();
  await page.locator('nav [data-view="profile"]').click();
  await page.getByLabel('Display name', {exact: true}).fill('Browser owner updated');
  await page.locator('#profile-form button').click();
  await expect(page.locator('#profile-button')).toContainText('Browser owner updated');
  await page.reload();
  await expect(page.locator('#profile-button')).toContainText('Browser owner updated');
  await page.locator('#logout').click();
  await expect(page.locator('#login')).toBeVisible();
  expect((await page.request.get('/api/overview')).status()).toBe(401);
});

test('create a timeline dashboard and reopen its saved definition after reload', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="dashboards"]').click();
  await page.locator('#studio-new').click();
  await page.getByLabel('Dashboard name', {exact: true}).fill('Browser incident dashboard');
  const editor = page.locator('#studio-panel-form');
  await editor.getByLabel('Panel title', {exact: true}).fill('Checkout errors');
  await editor.getByRole('combobox', {name: 'Signal', exact: true}).selectOption('logs');
  await editor.getByRole('combobox', {name: 'View', exact: true}).selectOption('timeline');
  await editor.getByRole('combobox', {name: 'Log severity', exact: true}).selectOption('ERROR');
  await editor.getByRole('button', {name: 'Add panel', exact: true}).click();
  await page.getByRole('button', {name: 'Save dashboard', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Checkout errors', exact: true})).toBeVisible();
  await expect(page.getByText('Browser fixture error', {exact: true})).toBeVisible();
  await page.reload();
  await expect(page.locator('#login')).toBeHidden();
  await page.locator('nav [data-view="dashboards"]').click();
  const saved = page.locator('.dashboard-card').filter({has: page.getByRole('heading', {name: 'Browser incident dashboard', exact: true})});
  await saved.getByRole('button', {name: 'Open →', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Checkout errors', exact: true})).toBeVisible();
  await expect(page.getByText('Browser fixture error', {exact: true})).toBeVisible();
});

test('log search renders untrusted markup as text without executing it', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="logs"]').click();
  const payload = '<img src=x onerror="window.__montralogXss=1">';
  await expect(page.getByText(payload, {exact: true})).toBeVisible();
  expect(await page.locator('img[src="x"]').count()).toBe(0);
  expect(await page.evaluate(() => window.__montralogXss)).toBeUndefined();
  await page.getByRole('textbox', {name: 'Search log messages', exact: true}).fill('Browser fixture');
  await page.getByRole('button', {name: 'Search', exact: true}).click();
  await expect(page.getByText('Browser fixture error', {exact: true})).toBeVisible();
  await expect(page.getByText(payload, {exact: true})).toHaveCount(0);
});

test('viewer cannot create machine tokens in the UI or access the admin API', async ({page}) => {
  await signIn(page, 'viewer');
  await page.locator('nav [data-view="api-tokens"]').click();
  await expect(page.getByText('Administrator access required', {exact: true})).toBeVisible();
  await expect(page.getByRole('button', {name: 'Create token', exact: true})).toHaveCount(0);
  expect((await page.request.get('/api/control/tokens')).status()).toBe(403);
});

test('investigations show captured evidence and keep model analysis optional', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="investigations"]').click();
  await expect(page.getByRole('heading', {name:'New investigation', exact:true})).toBeVisible();
  await page.locator('#investigation-create button').click();
  await expect(page.getByRole('heading', {name:'Observed evidence', exact:true})).toBeVisible();
  await expect(page.getByText('Browser fixture error', {exact:true})).toBeVisible();
  expect(await page.evaluate(() => window.__montralogXss)).toBeUndefined();
});
