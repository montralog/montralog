'use strict';
titles.investigations=['Investigate with evidence.','Correlate observed logs, traces and changes. Model output is a hypothesis, never a verified cause.'];
let investigationResult=null,runbookPlan=null;
let assistantOwner='';
function resetAssistantIdentity(){
 const owner=currentUser?.id||'';
 if(assistantOwner!==owner){investigationResult=null;runbookPlan=null;panelAssistantRun=null;document.querySelector('#ai-panel-dialog')?.remove();assistantOwner=owner;}
}
const beforeInvestigations=workspaceView;
function investigationReportHTML(result){
 if(!result)return '';
 const r=result.report,b=r.evidence,a=r.analysis;
 return `<section class="card"><div class="section-head"><h2>Investigation ${esc(result.id.slice(0,8))}</h2>${badge(result.status||'complete')}<button data-investigation-open="${esc(result.id)}">Refresh result</button></div><p>${esc(a.summary)}</p><small>${esc(r.provider)} / ${esc(r.model)} · ${result.cache_hit?'Reused evidence snapshot':'New evidence snapshot'} · Causality is not proven.</small>${(a.hypotheses||[]).map(h=>`<article class="pattern"><h3>${esc(h.claim)}</h3><p>Evidence: ${h.evidence_ids.map(id=>`<a href="#evidence-${esc(id.replace(/[^A-Za-z0-9]/g,'-'))}">${esc(id)}</a>`).join(', ')}</p><p><b>Uncertainty:</b> ${esc(h.uncertainty)}</p><p><b>Next check:</b> ${esc(h.next_check)}</p></article>`).join('')}<div class="callout">${fmt(b.noise.logs_in_window)} logs · ${fmt(b.noise.unique_patterns)} patterns · ${fmt(b.noise.repeated_records)} repeated records. Grouping reduces model input; original telemetry and alerting are not suppressed.</div>${agentDetailsHTML(r)}<h3>Observed evidence</h3>${b.evidence.length?b.evidence.map(item=>`<article class="pattern" id="evidence-${esc(item.id.replace(/[^A-Za-z0-9]/g,'-'))}"><b>${esc(item.id)} · ${esc(item.type)} · ${esc(item.service)}</b><small>${date(item.time)}${item.occurrences?' · '+fmt(item.occurrences)+' occurrences':''}</small><pre>${esc(item.message||item.name||'')}</pre></article>`).join(''):empty('Not enough evidence','Connect telemetry or choose another service/window.')}<details><summary>Token usage reported by provider</summary><pre>${esc(JSON.stringify(r.usage,null,2))}</pre></details></section><section class="card"><h2>Reviewed diagnostic runbook</h2><p>The model cannot run commands. The first allowlisted action rechecks an existing Prometheus connection without changing infrastructure. Review, approve and execute are separate steps.</p><form id="runbook-propose"><label>Saved source ID <input name="source_id" value="builtin" required maxlength="64"></label><button>Create read-only plan</button></form></section>`;
}
workspaceView=async function(next){
 resetAssistantIdentity();
 if(next!=='investigations')return beforeInvestigations(next);
 if(currentUser?.role!=='admin')return empty('Administrator access required','Evidence sharing, model budgets and runbook approval are restricted to administrators.');
 const [cfg,sources,rules,metrics]=await Promise.all([accountAPI('control/investigations'),accountAPI('control/data-sources'),accountAPI('control/rules'),api('dashboards')]);
 return `<div class="callout">Start with evidence only. Optional AI is operator-configured and requires explicit sharing approval for any hosted endpoint. No provider key is entered here. Automatic infrastructure remediation is disabled.</div><section class="card"><h2>New investigation</h2><p>Configured model: ${esc(cfg.provider)} / ${esc(cfg.model)} · ${cfg.enabled?'enabled':'disabled'}</p><form id="investigation-create" class="form-stack">${assistantFields(cfg,sources.items,rules.items,metrics.items,{})}<label>Service <input name="service" value="${esc($('#service').value)}" maxlength="200" placeholder="All services"></label><label>Environment <input name="environment" value="${esc($('#environment').value)}" maxlength="200" placeholder="All environments"></label><label>Log text contains <input name="q" maxlength="200"></label><label>Log severity <select name="severity"><option value="">All</option><option>ERROR</option><option>FATAL</option><option>WARN</option><option>INFO</option><option>DEBUG</option><option>TRACE</option></select></label><label>Window <select name="minutes"><option value="15">15 minutes</option><option value="30">30 minutes</option><option value="60">60 minutes</option></select></label><label><input name="use_model" type="checkbox" ${cfg.enabled?'':'disabled'}> Ask the configured model to analyze the selected evidence</label><label><input name="confirm_egress" type="checkbox"> I approve sharing this selected, redacted evidence with the configured hosted provider, if used</label><button class="primary">Collect and investigate</button></form></section>${investigationReportHTML(investigationResult)}<section class="card"><h2>Previous investigations</h2>${cfg.items.map(item=>`<p><button data-investigation-open="${esc(item.id)}">${esc(item.id.slice(0,8))}</button> ${badge(item.status)} ${esc(item.provider)} / ${esc(item.model)} · ${date(item.created_at)}</p>`).join('')||'<p>No investigations yet.</p>'}</section>${runbookPlan?`<section class="card"><h2>Review runbook ${esc(runbookPlan.id.slice(0,8))}</h2><pre>${esc(JSON.stringify(runbookPlan.definition,null,2))}</pre><form id="runbook-approve"><label>Type ${esc(runbookPlan.definition.confirmation)} <input name="confirmation" autocomplete="off" required></label><button>Approve reviewed plan</button></form><button id="runbook-execute" ${runbookPlan.state==='approved'?'':'disabled'}>Execute approved diagnostic</button></section>`:''}`;
};
document.addEventListener('submit',async event=>{
 const id=event.target.id;if(!['investigation-create','runbook-propose','runbook-approve'].includes(id))return;
 event.preventDefault();const button=event.submitter;if(button)button.disabled=true;
 try{
  const values=new FormData(event.target);
  if(id==='investigation-create'){investigationResult=await accountAPI('control/investigations',{service:values.get('service'),environment:values.get('environment'),minutes:Number(values.get('minutes')),use_model:values.has('use_model'),confirm_egress:values.has('confirm_egress'),...assistantValues(values)});runbookPlan=null;}
  if(id==='runbook-propose'){if(!investigationResult)throw Error('Open an investigation first.');runbookPlan=await accountAPI('control/runbooks',{action:'propose',run_id:investigationResult.id,source_id:values.get('source_id')});}
  if(id==='runbook-approve'){const approved=await accountAPI('control/runbooks',{action:'approve',id:runbookPlan.id,confirmation:values.get('confirmation')});runbookPlan.state=approved.state;}
  await render();formMessage('Investigation or runbook state saved. AI work is processed separately; refresh to inspect the result.');
 }catch(error){formMessage(error.message);}finally{if(button)button.disabled=false;}
});
document.addEventListener('click',async event=>{
 const b=event.target.closest('[data-investigation-open],#runbook-execute');if(!b)return;
 try{b.disabled=true;if(b.dataset.investigationOpen){investigationResult=await accountAPI('control/investigations',{action:'open',id:b.dataset.investigationOpen});runbookPlan=null;await render();}
 if(b.id==='runbook-execute'){const result=await accountAPI('control/runbooks',{action:'execute',id:runbookPlan.id});runbookPlan=null;await render();formMessage(result.result.message);}
 }catch(error){formMessage(error.message);}finally{b.disabled=false;}
});

function assistantFields(cfg,sources,rules,metrics,context){
 return `<label>Question<textarea name="question" maxlength="1200">${esc(context.question||'Explain the symptoms, identify missing evidence and recommend checks.')}</textarea></label><label>Approved model<select name="profile_id">${(cfg.profiles||[]).map(p=>`<option value="${esc(p.id)}">${esc(p.id||'Deployment default')} · ${esc(p.provider)} / ${esc(p.model)}</option>`).join('')}</select></label><label>Connected metric source<select name="source_id">${sources.map(p=>`<option value="${esc(p.id)}" ${p.id===context.source_id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label><label>Metric to inspect<select name="metric">${metrics.map(p=>`<option value="${esc(p.id)}" ${p.id===(context.metric||'cpu')?'selected':''}>${esc(p.title)}</option>`).join('')}</select></label><label>Related alert and runbook<select name="alert_id"><option value="">No linked alert</option>${rules.map(p=>`<option value="${esc(p.id)}" ${p.id===context.alert_id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label><label><input name="agentic" type="checkbox" checked> Allow bounded read-only metric inspection (up to three model calls)</label>`;
}
function assistantValues(values){return {q:values.get('q')||'',severity:values.get('severity')||'',question:values.get('question'),profile_id:values.get('profile_id')||'',source_id:values.get('source_id')||'',metric:values.get('metric')||'cpu',alert_id:values.get('alert_id')||'',agentic:values.has('agentic')};}
function agentDetailsHTML(report){
 const a=report.analysis;
 return `${report.context?`<p><b>Question:</b> ${esc(report.context.question)}</p><small>Connected source: ${esc(report.context.source_name)}. Source-wide metrics are not automatically attributable to a service.</small>`:''}${(a.hypotheses||[]).map(h=>(h.evidence_quotes||[]).map(q=>`<blockquote><b>${esc(q.id)}</b>: ${esc(q.quote)}</blockquote>`).join('')).join('')}${a.missing_evidence?.length?`<h3>Missing evidence</h3><ul>${a.missing_evidence.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:''}${report.tool_trace?.length?`<details><summary>Read-only investigation steps</summary><ul>${report.tool_trace.map(t=>`<li>${esc(t.tool)} · ${esc(t.metric)} → ${esc(t.evidence_id)}</li>`).join('')}</ul></details>`:''}`;
}
let panelAssistantRun=null;
function panelAssistantHTML(){
 if(!panelAssistantRun)return '';
 const result=panelAssistantRun,r=result.report,a=r.analysis;
 return `<section class="card"><h3>${esc(result.status)} · Evidence-linked advice</h3><p>${esc(a.summary)}</p>${(a.hypotheses||[]).map(h=>`<h3>${esc(h.claim)}</h3><p><b>Uncertainty:</b> ${esc(h.uncertainty)}</p><p><b>Recommended check:</b> ${esc(h.next_check)}</p>`).join('')}${agentDetailsHTML(r)}<p>Hypotheses are unverified. No infrastructure changes were made.</p><button id="panel-ai-refresh">Refresh analysis</button><button id="panel-ai-open">Open full evidence report</button></section>`;
}
async function openPanelAssistant(context){
 resetAssistantIdentity();
 document.querySelector('#ai-panel-dialog')?.remove();panelAssistantRun=null;
 const dialog=document.createElement('dialog');dialog.id='ai-panel-dialog';dialog.className='ai-assistant-dialog';
 document.body.appendChild(dialog);dialog.innerHTML='<p>Loading assistant…</p>';dialog.showModal();
 try{
  const [cfg,sources,rules,metrics]=await Promise.all([accountAPI('control/investigations'),accountAPI('control/data-sources'),accountAPI('control/rules'),api('dashboards')]);
  dialog.innerHTML=`<div class="section-head"><h2>Panel & alert assistant</h2><button id="panel-ai-close" aria-label="Close AI assistant">Close</button></div><p>Investigate connected data and runbook context. The assistant can inspect approved metrics, not execute remediation.</p><form id="panel-ai-create" class="form-stack">${assistantFields(cfg,sources.items,rules.items,metrics.items,context)}<input type="hidden" name="service" value="${esc(context.service||'')}"><input type="hidden" name="environment" value="${esc(context.environment||'')}"><input type="hidden" name="q" value="${esc(context.q||'')}"><input type="hidden" name="severity" value="${esc(context.severity||'')}"><small>Window: last ${Math.min(60,Math.max(1,Number(context.minutes)||15))} minutes, capped at 60. Log text and severity filters are inherited from the panel.</small><input type="hidden" name="minutes" value="${Math.min(60,Math.max(1,Number(context.minutes)||15))}"><label><input name="use_model" type="checkbox" ${cfg.enabled?'checked':'disabled'}> Use the selected model</label><label><input name="confirm_egress" type="checkbox"> I approve sharing the selected redacted evidence with a hosted model, if used</label><button class="primary">Investigate connected evidence</button></form><p id="panel-ai-notice" role="status"></p><div id="panel-ai-result"></div>`;
 }catch(error){dialog.textContent=error.message;const close=document.createElement('button');close.textContent='Close';close.onclick=()=>dialog.close();dialog.appendChild(close);}
}
document.addEventListener('submit',async event=>{
 if(event.target.id!=='panel-ai-create')return;
 event.preventDefault();const button=event.submitter;button.disabled=true;
 try{const values=new FormData(event.target);panelAssistantRun=await accountAPI('control/investigations',{...assistantValues(values),service:values.get('service'),environment:values.get('environment'),minutes:Number(values.get('minutes')),use_model:values.has('use_model'),confirm_egress:values.has('confirm_egress')});document.querySelector('#panel-ai-result').innerHTML=panelAssistantHTML();document.querySelector('#panel-ai-notice').textContent='Evidence saved. Refresh for the background analysis.';}
 catch(error){document.querySelector('#panel-ai-notice').textContent=error.message;}finally{button.disabled=false;}
});
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-ai-panel],[data-ai-alert],#panel-ai-close,#panel-ai-refresh,#panel-ai-open');if(!button)return;
 try{
  if(button.dataset.aiPanel)await openPanelAssistant(JSON.parse(decodeURIComponent(button.dataset.aiPanel)));
  if(button.dataset.aiAlert)await openPanelAssistant({alert_id:button.dataset.aiAlert,question:'Investigate this alert and evaluate its runbook checks.'});
  if(button.id==='panel-ai-close')document.querySelector('#ai-panel-dialog').close();
  if(button.id==='panel-ai-open'&&panelAssistantRun){investigationResult=panelAssistantRun;document.querySelector('#ai-panel-dialog').close();navigate('investigations');}
  if(button.id==='panel-ai-refresh'&&panelAssistantRun){panelAssistantRun=await accountAPI('control/investigations',{action:'open',id:panelAssistantRun.id});document.querySelector('#panel-ai-result').innerHTML=panelAssistantHTML();}
 }catch(error){const notice=document.querySelector('#panel-ai-notice');if(notice)notice.textContent=error.message;else formMessage(error.message);}
});
