"use strict";
(() => {
 const choices=['system','dark','light','midnight'], key='montralog.theme';
 const media=window.matchMedia('(prefers-color-scheme: light)');
 let selected='system';
 try { const saved=localStorage.getItem(key);if(choices.includes(saved))selected=saved; } catch {}

 function apply(){document.documentElement.dataset.theme=selected==='system'?(media.matches?'light':'dark'):selected;document.documentElement.dataset.themePreference=selected;const picker=document.getElementById('appearance-theme');if(picker)picker.value=selected;}
 document.addEventListener('change',event=>{if(event.target.id!=='appearance-theme')return;selected=choices.includes(event.target.value)?event.target.value:'system';try{localStorage.setItem(key,selected);}catch{}apply();});
 media.addEventListener('change',apply);
 window.addEventListener('storage',event=>{if(event.key===key){selected=choices.includes(event.newValue)?event.newValue:'system';apply();}});
 apply();
})();

function appearanceSettingsCard(){
 const selected=document.documentElement.dataset.themePreference||'system';
 return `<section class="card appearance-settings"><span class="eyebrow">PERSONAL PREFERENCES</span><h2>Appearance</h2><p>Choose how Montralog looks on this browser. System follows your device preference.</p><label for="appearance-theme">Theme</label><select id="appearance-theme">${[['system','System'],['dark','Dark'],['light','Light'],['midnight','Midnight']].map(([value,label])=>`<option value="${value}" ${value===selected?'selected':''}>${label}</option>`).join('')}</select><small>Saved automatically on this device.</small></section>`;
}
