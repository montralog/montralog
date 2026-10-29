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

test('alert runbooks persist and open the evidence assistant', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="alerts"]').click();
  await expect(page.locator('#studio-rule-form')).toBeVisible();
  await page.locator('#studio-rule-form [name="name"]').fill('Browser runbook alert');
  await page.locator('#studio-rule-form [name="runbook_summary"]').fill('Check the database dependency');
  await page.locator('#studio-rule-form [name="runbook_checks"]').fill('Inspect timeout logs\nCompare database health');
  await page.locator('#studio-rule-form [name="runbook_success"]').fill('Errors return to baseline');
  await page.getByRole('button',{name:'Save rule',exact:true}).click();
  const row=page.locator('tr').filter({hasText:'Browser runbook alert'});
  await expect(row).toBeVisible();
  await row.getByRole('button',{name:'Investigate',exact:true}).click();
  await expect(page.locator('#ai-panel-dialog')).toBeVisible();
  await expect(page.locator('#panel-ai-create [name="alert_id"]')).not.toHaveValue('');
  await page.locator('#panel-ai-create button').click();
  await expect(page.locator('#panel-ai-result')).toContainText('Evidence-linked advice');
  await page.getByRole('button',{name:'Close AI assistant',exact:true}).click();
  await row.getByRole('button',{name:'Edit',exact:true}).click();
  await expect(page.locator('#studio-rule-form [name="runbook_summary"]')).toHaveValue('Check the database dependency');
});

test('dashboard panels open a scoped assistant without leaving the dashboard', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="dashboards"]').click();
  const saved=page.locator('.dashboard-card').filter({has:page.getByRole('heading',{name:'Browser incident dashboard',exact:true})});
  await saved.getByRole('button',{name:'Open \u2192',exact:true}).click();
  await page.locator('[data-ai-panel]').first().click();
  await expect(page.locator('#ai-panel-dialog')).toBeVisible();
  await expect(page.locator('#panel-ai-create [name="question"]')).toHaveValue('Explain this panel: Checkout errors');
  await page.getByRole('button',{name:'Close AI assistant',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Checkout errors',exact:true})).toBeVisible();
});

test('empty canvas saves, pending panel edits persist, layout controls survive reload', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="dashboards"]').click();
  await page.locator('#studio-new').click();
  await page.getByLabel('Dashboard name', {exact:true}).fill('Builder regression dashboard');
  await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
  await expect(page.getByText('Your empty dashboard is saved.',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'＋ Add panel',exact:true}).click();
  const editor=page.locator('#studio-panel-form');
  await editor.getByLabel('Panel title',{exact:true}).fill('Pending log panel');
  await editor.getByRole('combobox',{name:'Signal',exact:true}).selectOption('logs');
  await editor.getByRole('combobox',{name:'View',exact:true}).selectOption('timeline');
  await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Pending log panel',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Edit dashboard',exact:true}).click();
  await page.locator('[data-panel-duplicate="0"]').click();
  await page.locator('[data-panel-resize="1"]').click();
  await page.locator('[data-panel-down="0"]').click();
  await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
  await expect(page.locator('#studio-dashboard-form')).toHaveCount(0);
  await page.reload();
  await page.locator('nav [data-view="dashboards"]').click();
  const card=page.locator('.dashboard-card').filter({has:page.getByRole('heading',{name:'Builder regression dashboard',exact:true})});
  await card.getByRole('button',{name:'Open →',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Pending log panel copy',exact:true})).toBeVisible();
  const saved=(await (await page.request.get('/api/saved-dashboards')).json()).items.find(d=>d.name==='Builder regression dashboard');
  expect(saved.definition.panels.map(p=>p.title)).toEqual(['Pending log panel copy','Pending log panel']);
  expect(saved.definition.panels[0].width).toBe('full');
});

test('failed dashboard save preserves the draft and allows a successful retry', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="dashboards"]').click();
  await page.locator('#studio-new').click();
  await page.getByLabel('Dashboard name',{exact:true}).fill('Retriable dashboard');
  let failed=false;
  await page.route('**/api/saved-dashboards',async route=>{
    if(route.request().method()==='POST'&&!failed){failed=true;await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Storage temporarily unavailable'})});}
    else await route.continue();
  });
  await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
  await expect(page.locator('#studio-builder-message')).toContainText('Storage temporarily unavailable');
  await expect(page.getByLabel('Dashboard name',{exact:true})).toHaveValue('Retriable dashboard');
  await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
  await expect(page.getByText('Your empty dashboard is saved.',{exact:false})).toBeVisible();
});

test('panel preview preserves input and sign out clears another account draft', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="dashboards"]').click();
  await page.locator('#studio-new').click();
  await page.getByLabel('Dashboard name',{exact:true}).fill('Private unsaved draft');
  await page.locator('#studio-panel-form').getByLabel('Panel title',{exact:true}).fill('Private panel draft');
  await page.getByRole('button',{name:'Preview panel',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Current panel preview',exact:true})).toBeVisible();
  await expect(page.locator('#studio-panel-form').getByLabel('Panel title',{exact:true})).toHaveValue('Private panel draft');
  await page.locator('#logout').click();
  await page.getByLabel('Username',{exact:true}).fill('viewer');
  await page.getByLabel('Password',{exact:true}).fill(password);
  await page.locator('#sign-in').click();
  await expect(page.locator('#login')).toBeHidden();
  await page.locator('nav [data-view="dashboards"]').click();
  await expect(page.getByText('Private unsaved draft',{exact:true})).toHaveCount(0);
  await page.locator('#studio-new').click();
  await expect(page.getByLabel('Dashboard name',{exact:true})).toHaveValue('Untitled dashboard');
});

test('about page includes bundled Apache license and preserves notice text safely', async ({page}) => {
  await signIn(page);
  await page.getByRole('button',{name:'About & license',exact:true}).click();
  await expect(page.getByRole('heading',{name:'About Montralog.',exact:true})).toBeVisible();
  await expect(page.getByText('Official project: https://github.com/montralog/montralog',{exact:false})).toBeVisible();
  await page.getByText('Apache License 2.0',{exact:true}).click();
  await expect(page.locator('.legal-copy').first()).toContainText('TERMS AND CONDITIONS');
  expect((await page.request.get('/license.txt')).headers()['content-type']).toContain('text/plain');
});

test('dashboard canvas stays visible and visual choices update live panel preview', async ({page}) => {
  await signIn(page);
  await page.locator('nav [data-view="dashboards"]').click();
  await page.locator('#studio-new').click();
  await page.getByLabel('Dashboard name',{exact:true}).fill('Visible canvas dashboard');
  const editor=page.getByRole('region',{name:'Panel editor',exact:true});
  await editor.getByLabel('Panel title',{exact:true}).fill('Visible stat');
  await editor.getByRole('button',{name:'Statistic',exact:true}).click();
  await expect(editor.getByRole('combobox',{name:'View',exact:true})).toHaveValue('stat');
  await expect(editor.getByRole('button',{name:'Statistic',exact:true})).toHaveAttribute('aria-pressed','true');
  await expect(editor.getByLabel('Service',{exact:true})).toBeHidden();
  await editor.getByRole('combobox',{name:'Signal',exact:true}).selectOption('logs');
  await expect(editor.getByLabel('Service',{exact:true})).toBeVisible();
  await expect(editor.getByRole('combobox',{name:'Metric',exact:true})).toBeHidden();
  await editor.getByRole('button',{name:'Timeline',exact:true}).click();
  await expect(page.locator('#studio-live-preview')).toContainText('Browser fixture error');
  await editor.getByRole('button',{name:'Add panel',exact:true}).click();
  await expect(editor).toHaveCount(0);
  await expect(page.locator('.dashboard-canvas').getByRole('heading',{name:'Visible stat',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
  await page.getByRole('button',{name:'Edit dashboard',exact:true}).click();
  await expect(page.getByRole('region',{name:'Panel editor',exact:true})).toHaveCount(0);
  await expect(page.locator('.dashboard-canvas')).toContainText('Visible stat');
  await page.getByRole('button',{name:'Edit panel',exact:true}).click();
  await expect(page.getByRole('region',{name:'Panel editor',exact:true})).toBeVisible();
});

test('themes persist and guided queries survive dashboard duplication and switching', async ({page}) => {
  await signIn(page);
  await page.getByLabel('Theme', {exact:true}).selectOption('light');
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await page.getByLabel('Theme', {exact:true}).selectOption('midnight');
  await expect(page.locator('html')).toHaveAttribute('data-theme','midnight');
  await page.locator('nav [data-view="dashboards"]').click();
  await page.locator('#studio-new').click();
  const name='Query builder '+Date.now();
  await page.getByLabel('Dashboard name',{exact:true}).fill(name);
  await page.getByRole('combobox',{name:'Metric',exact:true}).selectOption('targets');
  await page.getByRole('combobox',{name:'Aggregation',exact:true}).selectOption('avg');
  await page.getByRole('combobox',{name:'Group by',exact:true}).selectOption('instance');
  await expect(page.locator('#studio-generated-query')).toHaveText('avg by (instance) (up)');
  await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
  await page.locator('#studio-edit-dashboard').click();
  await page.getByRole('button',{name:'Edit panel',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'Aggregation',exact:true})).toHaveValue('avg');
  await expect(page.getByRole('combobox',{name:'Group by',exact:true})).toHaveValue('instance');
  await page.locator('#studio-hide-editor').click();
  await page.locator('#studio-cancel').click();
  await page.getByLabel('Find dashboard',{exact:true}).fill(name);
  const card=page.locator('.dashboard-card').filter({has:page.getByRole('heading',{name,exact:true})});
  await card.getByRole('button',{name:'Duplicate',exact:true}).click();
  await expect(page.getByLabel('Dashboard name',{exact:true})).toHaveValue(name+' copy');
  await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'Switch dashboard',exact:true})).toHaveValue(await page.getByRole('combobox',{name:'Switch dashboard',exact:true}).locator('option').filter({hasText:name+' copy'}).getAttribute('value'));
  await page.getByRole('combobox',{name:'Switch dashboard',exact:true}).selectOption({label:name});
  await expect(page.locator('#content h2').first()).toHaveText(name);
  await page.getByLabel('Theme',{exact:true}).selectOption('system');
  await page.emulateMedia({colorScheme:'light'});
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await page.emulateMedia({colorScheme:'dark'});
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
});


test('advanced gauge panels persist layout, context and safe references; catalog has real adapters',async({page})=>{
 await signIn(page);
 await page.locator('nav [data-view="dashboards"]').click();await page.locator('#studio-new').click();
 await page.getByLabel('Dashboard name',{exact:true}).fill('Advanced browser dashboard');
 const editor=page.getByRole('region',{name:'Panel editor',exact:true});
 await editor.getByLabel('Panel title',{exact:true}).fill('Host utilization');
 await editor.getByRole('button',{name:'Gauge',exact:true}).click();
 await editor.getByRole('combobox',{name:'Width',exact:true}).selectOption('third');
 await editor.getByRole('combobox',{name:'Height',exact:true}).selectOption('tall');
 await editor.getByRole('combobox',{name:'Panel icon',exact:true}).selectOption('server');
 await editor.getByRole('textbox',{name:'Description',exact:true}).fill('CPU context for operators');
 await editor.getByLabel('Reference URL',{exact:true}).fill('https://example.com/runbook');
 await editor.getByLabel('Warning threshold',{exact:true}).fill('65');
 await editor.getByRole('button',{name:'Add panel',exact:true}).click();
 await expect(page.locator('.dashboard-canvas > .panel-third')).toHaveCount(1);
 await page.getByRole('button',{name:'Save dashboard',exact:true}).click();
 await expect(page.getByRole('link',{name:'↗ Reference',exact:true})).toHaveAttribute('href','https://example.com/runbook');
 await page.reload();await page.locator('nav [data-view="dashboards"]').click();
 const card=page.locator('.dashboard-card').filter({has:page.getByRole('heading',{name:'Advanced browser dashboard',exact:true})});
 await card.getByRole('button',{name:'Edit',exact:true}).click();await page.getByRole('button',{name:'Edit panel',exact:true}).click();
 await expect(page.getByRole('combobox',{name:'View',exact:true})).toHaveValue('gauge');
 await expect(page.getByLabel('Warning threshold',{exact:true})).toHaveValue('65');
 await expect(page.getByRole('textbox',{name:'Description',exact:true})).toHaveValue('CPU context for operators');
 await page.locator('nav [data-view="connect"]').click();
 for(const name of ['Prometheus','VictoriaMetrics','Mimir','Thanos','Loki','Tempo'])await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Configure Loki →',exact:true}).click();
 await expect(page.getByRole('combobox',{name:'Backend type',exact:true})).toHaveValue('loki');
});
