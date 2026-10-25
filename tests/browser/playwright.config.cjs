const {defineConfig} = require('@playwright/test');
const path = require('node:path');
module.exports = defineConfig({
  testDir: __dirname, testMatch: '*.spec.cjs', workers: 1, retries: 0,
  timeout: 30000, outputDir: path.join(__dirname, 'test-results'),
  reporter: [['list'], ['html', {outputFolder: path.join(__dirname, 'playwright-report'), open: 'never'}]],
  use: {baseURL: 'http://127.0.0.1:8099', headless: true, trace: 'retain-on-failure'},
  webServer: {command: 'python tests/browser/server.py', cwd: path.resolve(__dirname, '../..'),
    url: 'http://127.0.0.1:8099/healthz', reuseExistingServer: false, timeout: 30000},
});
