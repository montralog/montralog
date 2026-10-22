'use strict';
let currentUser=null,csrf='',savedDashboards=[],activeDashboard=null;
Object.assign(titles,{
 dashboards:['Dashboards, built around your work.','Start with a template or assemble a personal view of your infrastructure.'],
 profile:['Make this workspace yours.','Manage your profile, password and active sessions.'],
 sources:['Know where your signals come from.','Inspect actual Prometheus scrape targets and observed telemetry sources.'],
 settings:['Your installation, at a glance.','Deployment details and the controls available to your operator.']
});
async function accountAPI(path,body){
 const res=await fetch('/api/'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const data=await res.json();if(res.status===401)showLogin('Sign in to continue.');if(!res.ok)throw Error(data.error||'Request failed');return data;
}
function showLogin(message=''){
 token='';currentUser=null;csrf='';epoch++;content.innerHTML='';document.body.classList.add('signed-out');$('#login').hidden=false;$('#controls').hidden=true;$('#password').value='';$('#login-notice').textContent=message;$('#login-notice').hidden=!message;
}
function enterWorkspace(data){
 currentUser=data.user;csrf=data.csrf;token='session';$('#password').value='';document.body.classList.remove('signed-out');$('#login').hidden=true;$('#controls').hidden=false;$('#profile-button').textContent=currentUser.name+' · Profile';navigate('overview');
}
function formMessage(message){$('#notice').textContent=message;$('#notice').hidden=false;}
const templates=[
 {id:'hosts',name:'Host essentials',description:'CPU and memory trends across your servers.',panels:['cpu','memory','host_disk']},
 {id:'containers',name:'Container operations',description:'Live Docker CPU, memory, processes, network totals and collection freshness.',panels:['docker_containers','container_cpu','docker_memory','docker_memory_percent','docker_processes','docker_received','docker_sent','agent_age']},
 {id:'kubernetes',name:'Kubernetes overview',description:'Pod phases by namespace with scrape target health.',panels:['pods','targets']},
 {id:'applications',name:'Application traffic',description:'Request throughput and telemetry collection health.',panels:['app_requests','targets']}
];
function metricValue(value,unit){
 const n=Number(value);if(!Number.isFinite(n))return 'No numeric sample';
 if(unit.includes('bytes')){const amount=n>=1073741824?(n/1073741824).toFixed(2)+' GiB':n>=1048576?(n/1048576).toFixed(2)+' MiB':n>=1024?(n/1024).toFixed(2)+' KiB':n.toFixed(0)+' B';return amount+(unit.includes('cumulative')?' total':'');}
 return esc(n.toLocaleString(undefined,{maximumFractionDigits:unit==='cores'?4:2})+' '+unit);
}
async function panelHTML(panel,minutes,readings={}){
 const r=await api('metrics',new URLSearchParams({panel,minutes})),s=r.data?.result||[];readings[panel]=s;
 return `<article class="card metric-card"><div class="section-head"><h2>${esc(r.panel?.title||panel)}</h2><span class="badge">${esc(r.panel?.unit||'')}</span></div>${s.length?s.slice().sort((a,b)=>Number(b.values.at(-1)[0])-Number(a.values.at(-1)[0])).slice(0,6).map(item=>`<div class="pattern"><small>${esc([item.metric.container_name,item.metric.container_id?.slice(0,8),item.metric.host_name||item.metric.instance].filter(Boolean).join(' · '))}</small><h3 class="green mono">${metricValue(item.values.at(-1)[1],r.panel?.unit||'')}</h3>${graph(item.values.filter(([,v])=>Number.isFinite(+v)).map(([time,value])=>({time,value:+value})),['value'])}</div>`).join(''):empty(r.available?'Waiting for matching metrics':'Metrics backend unavailable',r.error||'Connect the exporter for this panel. Templates never generate example values.',true)}${s.length>6?`<small>Showing 6 of ${s.length} series.</small>`:''}</article>`;
}
function dockerSnapshot(readings){
 if(!readings.docker_containers)return '';
 const latest=(series,name,host,id)=>{const item=(series||[]).find(s=>s.metric.container_name===name&&s.metric.host_name===host&&s.metric.container_id===id);return item?Number(item.values.at(-1)[1]):null;};
 const formatBytes=value=>value===null?'—':value>=1073741824?(value/1073741824).toFixed(2)+' GiB':(value/1048576).toFixed(2)+' MiB';
 const cpu=readings.container_cpu||[],now=Date.now()/1000;
 const ages=(readings.agent_age||[]).map(s=>Number(s.values.at(-1)[1])+Math.max(0,now-Number(s.values.at(-1)[0])));
 const fresh=ages.length&&Math.max(...ages)<60;
 const observed=new Map();for(const item of readings.docker_last_seen||[]){const key=item.metric.host_name+'/'+item.metric.container_name;const seen=Number(item.values.at(-1)[1]);if(now-seen<60&&(!observed.has(key)||seen>observed.get(key).seen))observed.set(key,{id:item.metric.container_id,seen});}
 const rows=cpu.filter(s=>s.metric.container_name&&observed.get(s.metric.host_name+'/'+s.metric.container_name)?.id===s.metric.container_id).map(s=>{const n=s.metric.container_name,h=s.metric.host_name,id=s.metric.container_id;const percent=latest(readings.docker_memory_percent,n,h,id),processes=latest(readings.docker_processes,n,h,id);return `<tr><td><b>${esc(n)}</b><small>${esc(h)}</small></td><td class="mono">${Number(s.values.at(-1)[1]).toFixed(4)}</td><td class="mono">${formatBytes(latest(readings.docker_memory,n,h,id))}</td><td>${percent===null?'—':percent.toFixed(2)+'%'}</td><td>${processes===null?'—':fmt(processes)}</td><td>${badge(fresh?'RECENT':'STALE')}</td></tr>`;});
 return `<section class="card builder"><div class="section-head"><div><h2>Running containers</h2><p>Latest observed values · updates every 15 seconds · CPU in core equivalents</p></div>${badge(fresh?'LIVE COLLECTION':'CHECK AGENT')}</div>${rows.length?table(['Container / host','CPU cores','Memory','Memory / limit','Processes','Collection'],rows):empty('No recent container measurements','Check the local metrics agent and Docker Desktop.')}<small>Docker reports approximate memory and I/O values. Network charts show cumulative totals, not transfer rates.</small></section><div class="section-head builder"><h2>Resource history</h2><span class="badge">PROMETHEUS</span></div>`;
}
async function workspaceView(next){
 if(next==='dashboards'){
  const [saved,defs]=await Promise.all([accountAPI('saved-dashboards'),api('dashboards')]);savedDashboards=saved.items;
  if(activeDashboard){
   const selected=activeDashboard,readings={};const panels=await Promise.all(selected.definition.panels.map(p=>panelHTML(p,selected.definition.minutes,readings)));if(selected.definition.panels.includes('docker_containers')){const seen=await api('metrics',new URLSearchParams({panel:'docker_last_seen',minutes:1}));readings.docker_last_seen=seen.data?.result||[];}
   return `<div class="section-head"><div><h2>${esc(selected.name)}</h2><p>Last ${selected.definition.minutes} minutes · all Prometheus resources · service filters do not apply</p></div><button id="dashboard-back">← Dashboard library</button></div>${dockerSnapshot(readings)}<div class="metric-grid">${panels.join('')}</div>`;
  }
  return `<div class="section-head"><div><h2>Your dashboards</h2><p>Saved to your account. Available after signing in on another device.</p></div><span class="badge">${saved.items.length} / 50 SAVED</span></div><div class="dashboard-grid">${saved.items.length?saved.items.map(d=>`<article class="card dashboard-card"><span class="eyebrow">PERSONAL DASHBOARD</span><h2>${esc(d.name)}</h2><p>${d.definition.panels.length} panel${d.definition.panels.length===1?'':'s'} · ${d.definition.minutes} minute window</p><div class="inline"><button class="primary" data-dashboard="${d.id}">Open dashboard →</button><button data-delete-dashboard="${d.id}" aria-label="Delete ${esc(d.name)}">Delete</button></div></article>`).join(''):empty('Your first dashboard starts below','Choose the signals that matter to your team.')}</div><div class="section-head"><h2>Start from a template</h2><span class="badge">LIVE DATA</span></div><div class="dashboard-grid">${templates.map(t=>`<article class="card dashboard-card"><div class="mini-chart" aria-hidden="true">▁ ▂ ▅ ▃ ▆ ▄ ▇ ▅</div><h2>${t.name}</h2><p>${t.description}</p><button data-template="${t.id}">Preview template →</button></article>`).join('')}</div><section class="card builder"><h2>Create a dashboard</h2><p>Choose panels and a default time window. No query language required.</p><form id="dashboard-form" class="form-stack"><label for="dashboard-name">Dashboard name</label><input id="dashboard-name" name="name" maxlength="80" required placeholder="e.g. Production infrastructure"><fieldset><legend>Metric panels</legend><div class="panel-options">${defs.items.map(p=>`<label class="check"><input type="checkbox" name="panel" value="${p.id}">${esc(p.title)}<small>${esc(p.unit)}</small></label>`).join('')}</div></fieldset><label for="dashboard-window">Default window</label><select name="minutes" id="dashboard-window"><option value="15">15 minutes</option><option value="60" selected>1 hour</option><option value="360">6 hours</option><option value="1440">24 hours</option></select><button class="primary">Save dashboard →</button></form></section>`;
 }
 if(next==='profile'){
  const [me,sessions]=await Promise.all([accountAPI('account'),accountAPI('account/sessions')]);currentUser=me.user;
  return `<div class="profile-hero card"><div class="avatar">${esc(currentUser.name.slice(0,2).toUpperCase())}</div><div><h2>${esc(currentUser.name)}</h2><p>@${esc(currentUser.username)} · Local account</p><small>Member since ${date(currentUser.created_at)}</small></div></div><div class="grid"><section class="card"><h2>Profile details</h2><p>Your email is a contact detail; email delivery is not configured.</p><form id="profile-form" class="form-stack"><label for="profile-name">Display name</label><input id="profile-name" name="name" value="${esc(currentUser.name)}" maxlength="100" required><label for="profile-email">Email (optional)</label><input id="profile-email" name="email" type="email" value="${esc(currentUser.email)}" maxlength="254"><label>Username</label><input aria-label="Username" value="${esc(currentUser.username)}" disabled><button class="primary">Save profile</button><small>Usernames are managed by the installation operator.</small></form></section><section class="card"><h2>Change password</h2><p>Updating your password signs out every session, including this one.</p><form id="password-form" class="form-stack"><label for="current-password">Current password</label><input id="current-password" name="current_password" type="password" autocomplete="current-password" required><label for="new-password">New password</label><input id="new-password" name="password" type="password" autocomplete="new-password" minlength="8" maxlength="256" required><label for="confirm-password">Confirm new password</label><input id="confirm-password" name="confirm" type="password" autocomplete="new-password" minlength="8" required><button>Update password</button></form></section></div><section class="card"><div class="section-head"><div><h2>Active sessions</h2><p>Sessions expire 12 hours after sign-in.</p></div><button id="revoke-sessions">Sign out other sessions</button></div>${table(['Session','Signed in','Expires'],sessions.items.map(s=>`<tr><td>${badge(s.current?'THIS DEVICE':'OTHER SESSION')}</td><td>${date(s.created_at)}</td><td>${date(s.expires_at)}</td></tr>`))}</section>`;
 }
 if(next==='sources'){
  const [targets,overview]=await Promise.all([api('targets'),api('overview')]);const items=targets.data?.activeTargets||[];
  return `<div class="stats"><div class="card stat"><span class="label">Scrape targets</span><strong>${items.length}</strong><small>From Prometheus discovery</small></div><div class="card stat"><span class="label">Targets up</span><strong class="green">${items.filter(t=>t.health==='up').length}</strong><small>Last scrape result</small></div><div class="card stat"><span class="label">Targets down</span><strong class="red">${items.filter(t=>t.health==='down').length}</strong><small>Needs investigation</small></div><div class="card stat"><span class="label">Observed services</span><strong>${overview.services.length}</strong><small>Within selected telemetry window</small></div></div><section class="card"><div class="section-head"><h2>Prometheus targets</h2><button data-go="connect">Connect a source →</button></div>${!targets.available?empty('Backend unavailable',targets.error):items.length?table(['Job / instance','State','Last scrape','Evidence'],items.map(t=>`<tr><td><b>${esc(t.labels?.job)}</b><small class="mono">${esc(t.labels?.instance)}</small></td><td>${badge(t.health)}</td><td>${esc(t.lastScrape)}</td><td class="message">${esc(t.lastError||'Last scrape completed without an error.')}</td></tr>`)):empty('No scrape targets','Configure exporters in your Prometheus deployment.',true)}</section><section class="card builder"><h2>Observed log sources</h2><p>Sources are discovered from received telemetry. This list reflects the selected time window.</p>${serviceTable(overview.services)}</section>`;
 }
 const [health,defs]=await Promise.all([fetch('/healthz').then(r=>r.json()),api('dashboards')]);
 return `<div class="grid"><section class="card"><h2>Installation</h2>${table(['Setting','Value'],[['Version',health.version],['Deployment','Self-hosted'],['Account access','Operator-managed local accounts'],['Browser session','HttpOnly cookie · 12 hour expiry'],['Supported metric panels',defs.items.length],['License','Apache License 2.0']].map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`))}</section><section class="card"><h2>Operator controls</h2><p>Configuration belongs to your deployment and is applied through Docker Compose or Helm.</p><div class="pattern"><h3>Retention & backups</h3><small>Set RETENTION_DAYS for logs, spans, host samples and change events. Configure Prometheus retention separately. Follow docs/OPERATIONS.md for backups.</small></div><div class="pattern"><h3>Notifications</h3><small>Set an Alertmanager receiver in deploy/docker/alertmanager.yml before relying on alert delivery.</small></div><div class="pattern"><h3>Accounts & access</h3><small>Create local accounts using the operator CLI. Accounts share read access to telemetry and own their personal dashboards. Fine-grained roles and SSO are not available in this release.</small></div><div class="pattern"><h3>Network & HTTPS</h3><small>Local Docker ports bind to loopback. When exposing the UI, use HTTPS and set MONTRALOG_COOKIE_SECURE=true.</small></div></section></div>`;
}
$('#login-form').addEventListener('submit',async e=>{
 e.preventDefault();const button=$('#sign-in');button.disabled=true;$('#login-notice').hidden=true;
 try{const res=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:$('#username').value,password:$('#password').value})});const d=await res.json();if(!res.ok)throw Error(d.error);enterWorkspace(d);}catch(err){$('#login-notice').textContent=err.message;$('#login-notice').hidden=false;}finally{button.disabled=false;}
});
document.addEventListener('submit',async e=>{
 if(!['dashboard-form','profile-form','password-form'].includes(e.target.id))return;e.preventDefault();const form=e.target,button=form.querySelector('button');button.disabled=true;
 try{const values=new FormData(form);
  if(form.id==='dashboard-form'){await accountAPI('saved-dashboards',{name:values.get('name'),definition:{panels:values.getAll('panel'),minutes:Number(values.get('minutes'))}});activeDashboard=null;epoch++;await render();formMessage('Dashboard saved to your account.');}
  if(form.id==='profile-form'){const d=await accountAPI('account/profile',{name:values.get('name'),email:values.get('email')});currentUser=d.user;$('#profile-button').textContent=d.user.name+' · Profile';formMessage('Profile saved.');}
  if(form.id==='password-form'){if(values.get('password')!==values.get('confirm'))throw Error('New passwords do not match.');await accountAPI('account/password',{current_password:values.get('current_password'),password:values.get('password')});showLogin('Password updated. Sign in with your new password.');}
 }catch(err){formMessage(err.message);}finally{button.disabled=false;}
});
document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b)return;
 try{
  if(b.id==='logout'||b.dataset.action==='logout'){await accountAPI('account/logout',{});showLogin('You have signed out.');}
  if(b.id==='revoke-sessions'){await accountAPI('account/revoke',{});epoch++;await render();formMessage('Other sessions signed out.');}
  if(b.dataset.dashboard){activeDashboard=savedDashboards.find(d=>d.id===b.dataset.dashboard);epoch++;render();}
  if(b.dataset.template){const t=templates.find(t=>t.id===b.dataset.template);activeDashboard={name:t.name,definition:{panels:t.panels,minutes:60}};epoch++;render();}
  if(b.id==='dashboard-back'){activeDashboard=null;epoch++;render();}
  if(b.dataset.deleteDashboard){if(!confirm('Delete this personal dashboard?'))return;await accountAPI('saved-dashboards/delete',{id:b.dataset.deleteDashboard});epoch++;render();}
 }catch(err){formMessage(err.message);}
});
(async()=>{try{const status=await fetch('/api/auth/status').then(r=>r.json());$('#first-run').hidden=status.configured;const res=await fetch('/api/account');if(res.ok)enterWorkspace(await res.json());}catch{showLogin('Cannot reach Montralog. Check the local Docker services.');}})();
