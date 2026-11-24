'use strict';
// Date boundary, opening and closing in Taiwan, independent of browser timezone.
const electionMidnight=Date.parse('2026-11-28T00:00:00+08:00'), electionOpen=Date.parse('2026-11-28T08:00:00+08:00'), electionClose=Date.parse('2026-11-28T16:00:00+08:00');
function countdownState(now){
 const phase=now<electionMidnight?'date':now<electionOpen?'opening':now<electionClose?'closing':'ended';
 const target={date:electionMidnight,opening:electionOpen,closing:electionClose,ended:electionClose}[phase];
 const remaining=Math.max(0,Math.ceil((target-now)/1000));
 return {phase,days:Math.floor(remaining/86400),hours:Math.floor(remaining/3600)%24,minutes:Math.floor(remaining/60)%60,seconds:remaining%60};
}
const byId=id=>document.getElementById(id);
function tick(){const t=countdownState(Date.now());byId('countdown-label').textContent={date:'距離投票日期還有',opening:'距離投票開始還有',closing:'距離投票截止還有',ended:'2026 年 11 月 28 日'}[t.phase];byId('countdown-clock').hidden=t.phase==='ended';byId('countdown-ended').hidden=t.phase!=='ended';for(const k of ['days','hours','minutes','seconds'])byId(k).textContent=String(t[k]).padStart(2,'0');}
tick();const timer=setInterval(tick,1000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)tick()});
const search=byId('county-search'),region=byId('region'),count=byId('count'),empty=byId('empty');
const cards=[...document.querySelectorAll('.county')],grid=document.querySelector('.county-grid'),panel=byId('county-panel'),office=byId('office');
const normalize=s=>s.normalize('NFKC').replaceAll('台','臺').trim();
let selected=null;
function clearSelection(restoreFocus=false){const old=selected?.button;selected=null;panel.hidden=true;for(const b of grid.querySelectorAll('button'))b.setAttribute('aria-pressed','false');if(restoreFocus){if(old&&!old.parentElement.hidden)old.focus();else search.focus();}}
function filter(){const q=normalize(search.value);let visible=0;for(const card of cards){const match=normalize(card.dataset.name).includes(q)&&(!region.value||card.dataset.region===region.value);card.hidden=!match;if(match)visible++}if(selected?.button.parentElement.hidden)clearSelection();count.textContent=visible===cards.length?'22 縣市':visible+' / 22 縣市';empty.hidden=visible!==0;}
let chiefSources={};try{chiefSources=JSON.parse(byId("chief-sources").textContent)}catch{}
let data;try{data=JSON.parse(byId('elector-data').textContent)}catch{data=null;}
function show(){if(!selected)return;const i=Number(office.value),n=data.counties[selected.name][i];byId('elector-value').textContent=n.toLocaleString('en-US');byId('elector-label').textContent=i===5?'投票權人人數':'選舉人人數';byId('elector-category').textContent=data.labels[i]+(n===0?' · 官方統計為 0':'');byId('elector-source').href=i===5?data.referendum_pdf:data.local_pdf;}
function selectCounty(card,button,url){if(selected?.button===button){clearSelection(true);return;}selected={name:card.dataset.name,button};for(const b of grid.querySelectorAll('button'))b.setAttribute('aria-pressed',String(b===button));byId('selected-county').textContent=selected.name;byId('selected-link').href=url;const notice=byId("chief-notice");const source=chiefSources[selected.name];notice.hidden=!(typeof source==="string"&&source.startsWith("https://web.cec.gov.tw/"));if(!notice.hidden)notice.href=source;else notice.removeAttribute("href");panel.hidden=false;show();byId('selected-county').focus({preventScroll:true});panel.scrollIntoView({block:'nearest'});}
if(data&&cards.length===22&&cards.every(c=>Array.isArray(data.counties?.[c.dataset.name])&&data.counties[c.dataset.name].length===6&&data.counties[c.dataset.name].every(n=>Number.isInteger(n)&&n>=0))){
 for(const card of cards){const a=card.querySelector('a'),url=a.href;const b=document.createElement('button');b.type='button';b.textContent=card.dataset.name;b.setAttribute('aria-pressed','false');b.setAttribute('aria-controls','county-panel');card.replaceChildren(b);b.addEventListener('click',()=>selectCounty(card,b,url));}
 office.addEventListener('change',show);byId('clear-county').addEventListener('click',()=>clearSelection(true));
}
search.addEventListener('input',filter);region.addEventListener('change',filter);byId('reset').addEventListener('click',()=>{search.value='';region.value='';clearSelection();filter();search.focus()});filter();
