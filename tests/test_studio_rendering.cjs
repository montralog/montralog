const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function studio(response) {
  const requests = [];
  const context = vm.createContext({
    URL, URLSearchParams, showLogin() {}, titles: {}, workspaceView: async () => '',
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


test('identical metric panels share a request and distinct sources remain isolated', async () => {
  const {context,requests}=studio({available:true,panel:{unit:'state'},data:{result:[]}});
  const p={source:'metric',metric:'targets',visual:'line',datasource:'a',aggregation:'avg',group_by:'instance'};
  await Promise.all([context.studioPanel(p,60),context.studioPanel({...p,visual:'stat'},60)]);
  assert.equal(requests.length,1);
  assert.equal(requests[0].params.get('aggregation'),'avg');
  assert.equal(requests[0].params.get('group_by'),'instance');
  await context.studioPanel({...p,datasource:'b'},60);
  assert.equal(requests.length,2);
});


test('gauge clamps geometry, labels critical values and escapes descriptions and references',async()=>{
 const {context}=studio({available:true,panel:{unit:'%'},data:{result:[{metric:{host_name:'api'},values:[[1,'150']]}]}});
 const html=await context.studioPanel({source:'metric',metric:'cpu',visual:'gauge',min:0,max:100,warning:70,critical:90,width:'third',height:'tall',description:'<script>bad</script>',reference:'javascript:bad'},60);
 assert.match(html,/gauge critical/);assert.match(html,/width="300" height="16" rx="8" class="gauge-fill"/);
 assert.match(html,/panel-third panel-height-tall/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/href="javascript:/);
 assert.match(context.referenceHTML({reference:'https://example.com/docs'}),/rel="noopener noreferrer"/);
});
