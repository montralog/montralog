"use strict";
(() => {
 const choices=['system','dark','light','midnight'], key='montralog.theme';
 const media=window.matchMedia('(prefers-color-scheme: light)');
 let selected='system';
 try { const saved=localStorage.getItem(key);if(choices.includes(saved))selected=saved; } catch {}
 const picker=document.getElementById('appearance-theme');
 function apply(){document.documentElement.dataset.theme=selected==='system'?(media.matches?'light':'dark'):selected;if(picker)picker.value=selected;}
 picker?.addEventListener('change',()=>{selected=choices.includes(picker.value)?picker.value:'system';try{localStorage.setItem(key,selected);}catch{}apply();});
 media.addEventListener('change',apply);
 window.addEventListener('storage',event=>{if(event.key===key){selected=choices.includes(event.newValue)?event.newValue:'system';apply();}});
 apply();
})();
