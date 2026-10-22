'use strict';
let connectionMode='list',connectionEdit=null,connectionNotice='',connectionNoticeOK=true,connectionBusy=false;
const workspaceBeforeConnections=workspaceView;
titles.connect=['Connect your data.','Choose a source, configure its connection, and test it before building panels.'];
titles.sources=['Your data connections.','Manage saved sources, authentication and the workspace default.'];
function connectionStatus(item){return item.last_status==='connected'?'<span class="badge good">TEST PASSED</span>':item.last_status==='error'?'<span class="badge error">TEST FAILED</span>':'<span class="badge">BUILT-IN</span>';}
function connectionForm(){
 const c=connectionEdit||{name:'',url:'',auth_type:'none',username:'',is_default:1};
 return `<div class="connection-steps"><span>01 &nbsp; Choose source</span><b>02 &nbsp; Configure & test</b><span>03 &nbsp; Build panels</span></div><div class="section-head"><div><h2>Connect Prometheus</h2><p>A server-side connection to your existing metrics backend.</p></div><button id="connection-back">← Connections</button></div><div class="grid"><section class="card"><form id="connection-form" class="form-stack"><label for="connection-name">Connection name</label><input id="connection-name" name="name" required maxlength="80" value="${esc(c.name)}" placeholder="e.g. Production metrics"><label for="connection-url">Prometheus server URL</label><input id="connection-url" name="url" required type="url" value="${esc(c.url)}" placeholder="http://prometheus:9090"><small>Use an address reachable from the Montralog server. For a service on your Windows host, use host.docker.internal instead of localhost.</small><button type="button" id="connection-bundled">Use local Docker Prometheus</button><label for="connection-auth">Authentication</label><select id="connection-auth" name="auth_type">${options([['none','No authentication'],['basic','Username and password'],['bearer','Bearer credential']],c.auth_type)}</select><div id="connection-auth-fields" class="form-stack" ${c.auth_type==='none'?'hidden':''}><div id="connection-username-wrap" ${c.auth_type!=='basic'?'hidden':''}><label for="connection-username">Server username</label><input id="connection-username" name="username" maxlength="200" value="${esc(c.username)}" autocomplete="off"></div><label for="connection-secret">${c.auth_type==='bearer'?'Server bearer credential':'Server password'}</label><input id="connection-secret" name="secret" type="password" maxlength="8192" autocomplete="new-password" placeholder="${c.id?'Leave empty to keep the saved credential':'Only required when the server uses authentication'}"><small>Credentials stay on the server and are never returned to the browser.</small></div><label class="check"><input type="checkbox" name="is_default" ${c.is_default?'checked':''}>Use as workspace default for metrics and alert queries</label><div class="inline"><button type="button" id="connection-test">Test connection</button><button class="primary" type="submit">Save & test →</button></div></form></section><section class="card connection-guide"><span class="source-icon">P</span><h2>Prometheus</h2><p>Connect once. Reuse the source across dashboards, infrastructure views and panels.</p><div class="pattern"><h3>1. Enter the server address</h3><small>Your bundled local backend is http://prometheus:9090. Remote servers can use an HTTPS URL, including a reverse-proxy path.</small></div><div class="pattern"><h3>2. Choose authentication only if needed</h3><small>Local Prometheus normally needs no credential. Basic and bearer authentication are available for protected backends.</small></div><div class="pattern"><h3>3. Save & test</h3><small>Montralog runs a real query against the server. A working connection can still return no metrics until exporters are configured.</small></div><div class="pattern"><h3>4. Choose it in a panel</h3><small>Metric panels have a Data source selector. Existing panels use your workspace default unless they select a specific source.</small></div></section></div>`;
}
async function connectionView(next){
 const data=await accountAPI('control/data-sources');connectionSources=data.items;
 const admin=currentUser?.role==='admin';
 const notice=connectionNotice?`<div class="callout ${connectionNoticeOK?'':'warning'}" role="status"><strong>${connectionNoticeOK?'✓':'!'} ${esc(connectionNotice)}</strong></div>`:'';
 if(connectionMode==='edit')return notice+(admin?connectionForm():empty('Administrator access required','An administrator can configure data-source connections.'));
 const saved=`<section class="card"><div class="section-head"><div><h2>Connected sources</h2><p>Credentials are managed on the server. Test status records the last connection check.</p></div>${admin?'<button class="primary" id="connection-add">＋ Add connection</button>':''}</div>${table(['Connection','Server','Authentication','Last test',''],data.items.map(c=>`<tr><td><b>${esc(c.name)}</b><small>Prometheus ${c.is_default?'· WORKSPACE DEFAULT':''}</small></td><td class="mono message">${esc(c.url||'Not configured')}</td><td>${esc(c.auth_type==='none'?'None':c.auth_type==='basic'?'Basic · password hidden':'Bearer · secret hidden')}</td><td>${connectionStatus(c)}<small>${c.last_checked?date(c.last_checked):esc(c.last_detail)}</small></td><td><div class="inline">${admin?`<button data-connection-test="${c.id}">Test</button><button data-connection-edit="${c.id}">${c.id==='builtin'?'Customize':'Edit'}</button>${c.id!=='builtin'?`<button data-connection-delete="${c.id}">Delete</button>`:''}`:''}<button data-connection-explore="${c.id}">Explore →</button></div></td></tr>`))}</section>`;
 const catalog=`<div class="section-head"><div><h2>Add a connection</h2><p>Start with a backend or explore the sources already built into your installation.</p></div><span class="badge">LOCAL WORKSPACE</span></div><div class="source-catalog"><article class="card source-card"><span class="source-icon">P</span><h2>Prometheus</h2><p>Connect your metrics server. Test the address, save authentication if needed, and choose a default.</p><span class="badge good">CONFIGURABLE CONNECTION</span>${admin?'<button class="primary" id="connection-add-prometheus">Add connection →</button>':'<small>Ask your administrator to configure a source.</small>'}</article><article class="card source-card"><span class="source-icon">≡</span><h2>Montralog logs</h2><p>Your stored logs and recurring message patterns are already available through your account.</p><span class="badge">BUILT-IN STORAGE</span><button data-go="logs">Explore logs →</button></article><article class="card source-card"><span class="source-icon">⌁</span><h2>Montralog traces</h2><p>Explore recorded OpenTelemetry request traces and follow links back to related logs.</p><span class="badge">BUILT-IN STORAGE</span><button data-go="traces">Explore traces →</button></article><article class="card source-card"><span class="source-icon">▦</span><h2>Docker & host</h2><p>Your local collector feeds the bundled Prometheus connection. Open the saved resource dashboard.</p><span class="badge">LOCAL COLLECTION</span><button id="connection-local-dashboard">Open Docker dashboard →</button></article></div>`;
 let targets='';
 if(next==='sources'){
  const result=await api('targets'),items=result.data?.activeTargets||[];
  targets=`<section class="card builder"><h2>Default source scrape targets</h2><p>Live status from the selected default Prometheus server.</p>${!result.available?empty('Backend unavailable',result.error):items.length?table(['Job / instance','State','Last scrape','Detail'],items.map(t=>`<tr><td>${esc(t.labels?.job)}<small>${esc(t.labels?.instance)}</small></td><td>${badge(t.health)}</td><td>${esc(t.lastScrape)}</td><td class="message">${esc(t.lastError||'Last scrape succeeded')}</td></tr>`)):empty('No targets reported','Connect exporters to this Prometheus instance.')}</section>`;
 }
 return notice+(next==='connect'?catalog+saved:saved+'<div class="builder">'+catalog+'</div>')+targets;
}
workspaceView=async function(next){return ['connect','sources'].includes(next)?connectionView(next):workspaceBeforeConnections(next);};
function connectionValues(action){const v=new FormData($('#connection-form'));return {action,id:connectionEdit?.id||'',name:v.get('name'),url:v.get('url'),auth_type:v.get('auth_type'),username:v.get('username')||'',secret:v.get('secret')||'',is_default:v.has('is_default')};}
async function testOrSaveConnection(action){
 if(connectionBusy)return;
 const form=$('#connection-form');if(!form.reportValidity())return;connectionBusy=true;
 const buttons=[...form.querySelectorAll('button')];buttons.forEach(b=>b.disabled=true);
 try{
  const d=await accountAPI('control/data-sources',connectionValues(action));connectionNotice=d.message;connectionNoticeOK=d.ok;
  if(action==='save'&&d.ok){connectionMode='list';connectionEdit=null;epoch++;await render();}
  else{formMessage(d.message);$('#notice').classList.toggle('connection-success',d.ok);}
 }catch(err){formMessage(err.message);$('#notice').classList.remove('connection-success');}
 finally{connectionBusy=false;buttons.forEach(b=>b.disabled=false);}
}
document.addEventListener('change',e=>{
 if(e.target.id==='connection-auth'){
  const mode=e.target.value;$('#connection-auth-fields').hidden=mode==='none';$('#connection-username-wrap').hidden=mode!=='basic';
  $('label[for="connection-secret"]').textContent=mode==='bearer'?'Server bearer credential':'Server password';
 }
});
document.addEventListener('submit',e=>{if(e.target.id==='connection-form'){e.preventDefault();testOrSaveConnection('save');}});
document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b)return;
 try{
  if(b.id==='connection-test'){await testOrSaveConnection('test');return;}
  if(b.id==='connection-bundled'){$('#connection-url').value=connectionSources.find(c=>c.id==='builtin')?.url||'http://prometheus:9090';if(!$('#connection-name').value)$('#connection-name').value='Local Prometheus';return;}
  if(['connection-add','connection-add-prometheus'].includes(b.id)){connectionMode='edit';connectionEdit=null;connectionNotice='';}
  else if(b.id==='connection-back'){connectionMode='list';connectionEdit=null;}
  else if(b.dataset.connectionEdit){const selected=connectionSources.find(c=>c.id===b.dataset.connectionEdit);connectionEdit=selected.id==='builtin'?{name:'Local Prometheus',url:selected.url,auth_type:'none',username:'',is_default:1}:{...selected};connectionMode='edit';connectionNotice='';}
  else if(b.dataset.connectionTest){b.disabled=true;const d=await accountAPI('control/data-sources',{action:'test-saved',id:b.dataset.connectionTest});connectionNotice=d.message;connectionNoticeOK=d.ok;}
  else if(b.dataset.connectionDelete){if(!confirm('Delete this connection? Panels that explicitly select it will report it as missing.'))return;await accountAPI('control/data-sources',{action:'delete',id:b.dataset.connectionDelete});connectionNotice='Connection deleted.';connectionNoticeOK=true;}
  else if(b.dataset.connectionExplore){studioDefs=(await api('dashboards')).items;activeDashboard={name:connectionSources.find(c=>c.id===b.dataset.connectionExplore)?.name||'Metrics',definition:{minutes:60,panels:[{source:'metric',metric:'targets',visual:'table',title:'Scrape target health',datasource:b.dataset.connectionExplore,width:'full'}]}};dashboardDraft=null;navigate('dashboards');return;}
  else if(b.id==='connection-local-dashboard'){const d=await accountAPI('saved-dashboards');activeDashboard=d.items.find(x=>x.name.includes('Local Docker'))||{name:'Local Docker',definition:{minutes:15,panels:['docker_containers','container_cpu','docker_memory','agent_age']}};dashboardDraft=null;navigate('dashboards');return;}
  else return;
  epoch++;await render();
 }catch(err){formMessage(err.message);}finally{b.disabled=false;}
});
