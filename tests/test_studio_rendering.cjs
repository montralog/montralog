const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function studio(response) {
  const requests = [];
  const context = vm.createContext({
    URLSearchParams, titles: {}, workspaceView: async () => '',
    document: {addEventListener() {}},
    esc: value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;'),
    date: value => String(value), fmt: value => String(value),
    empty: title => `<p>${title}</p>`,
    metricValue: (value, unit) => `${value}${unit}`,
    api: async (name, params) => {requests.push({name, params}); return response;},
    graph: () => '<svg data-line-chart></svg>',
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/montralog/static/studio.js'), 'utf8'), context);
  return {context, requests};
}

test('stat panel renders the selected source and latest sample without a line chart', async () => {
  const {context, requests} = studio({available: true, panel: {unit: '%'}, data: {
    result: [{metric: {host_name: 'web-1'}, values: [[1, '20'], [2, '42']]}]}});
  const html = await context.studioPanel({source: 'metric', metric: 'cpu', visual: 'stat', datasource: 'selected'}, 15);
  assert.match(html, /<strong>42%<\/strong>/);
  assert.match(html, /web-1/);
  assert.doesNotMatch(html, /data-line-chart/);
  assert.equal(requests[0].params.get('datasource'), 'selected');
  assert.equal(requests[0].params.get('minutes'), '15');
});

test('bar panels omit nonfinite samples instead of emitting broken SVG geometry', async () => {
  const {context} = studio({available: true, panel: {unit: '%'}, data: {result: [
    {metric: {host_name: 'missing'}, values: [[1, 'NaN']]},
    {metric: {host_name: 'overflow'}, values: [[1, '+Inf']]},
    {metric: {host_name: 'healthy'}, values: [[1, '40']]},
  ]}});
  const html = await context.studioPanel({source: 'metric', metric: 'cpu', visual: 'bar'}, 15);
  assert.match(html, /healthy/);
  assert.doesNotMatch(html, /NaN|Infinity|missing|overflow/);
  assert.match(html, /width="500" height="12" fill="#68e4b0"/);
});

test('a bar panel with only unavailable samples explains the empty state', () => {
  const {context} = studio({});
  assert.match(context.barsHTML([{label: 'missing', value: NaN}]), /No finite samples/);
});
