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
function tick(){const t=countdownState(Date.now());byId('countdown-label').textContent={date:'距離投票日期還有',opening:'距離投票開始還有',closing:'距離投票截止還有',ended:'2026 年 11 月 28 日'}[t.phase];byId('countdown-clock').hidden=t.phase==='ended';byId('countdown-ended').hidden=t.phase!=='ended';const bring=byId('bring');if(bring)bring.hidden=t.phase==='ended';for(const k of ['days','hours','minutes','seconds'])byId(k).textContent=String(t[k]).padStart(2,'0');}
tick();const timer=setInterval(tick,1000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)tick()});
const cards=[...document.querySelectorAll('.county')],grid=document.querySelector('.county-grid'),panel=byId('county-panel'),office=byId('office');
let selected=null;
function clearSelection(restoreFocus=false){const old=selected?.button;selected=null;panel.hidden=true;document.dispatchEvent(new Event('countychange'));for(const b of grid.querySelectorAll('button'))b.setAttribute('aria-pressed','false');if(restoreFocus){if(old)old.focus();}}
let chiefSources={};try{chiefSources=JSON.parse(byId("chief-sources").textContent)}catch{}
let data;try{data=JSON.parse(byId('elector-data').textContent)}catch{data=null;}
function show(){if(!selected)return;const i=Number(office.value),n=data.counties[selected.name][i];const code=selected.code;const roles=['chief','council','town-chief','town-rep','village',''];const role=(Number(code)<=6&&i===2)?'district-chief':(Number(code)<=6&&i===3)?'district-rep':roles[i];const a=byId('selected-link');a.hidden=i===5||((i===2||i===3)&&n===0);byId('chief-notice').hidden=i!==0||!byId('chief-notice').hasAttribute('href');if(i!==5)a.href='gazettes.html?county='+code+'&office='+encodeURIComponent(role);byId('elector-value').textContent=n.toLocaleString('en-US');byId('elector-label').textContent=i===5?'投票權人人數':'選舉人人數';byId('elector-category').textContent=data.labels[i]+(n===0?' · 官方統計為 0':'');byId('elector-source').href=i===5?data.referendum_pdf:data.local_pdf;document.dispatchEvent(new Event('countychange'));}
function selectCounty(card,button,url,focus=true){if(selected?.button===button){clearSelection(true);return;}const code=new URL(url).searchParams.get('dir')?.match(/^115\/(\d{2})/)?.[1];if(!code)return;selected={name:card.dataset.name,button,code};for(const b of grid.querySelectorAll('button'))b.setAttribute('aria-pressed',String(b===button));byId('selected-county').textContent=selected.name;byId('official-directory').href=url;const notice=byId('chief-notice');const src=chiefSources[selected.name];notice.hidden=!(typeof src==='string'&&src.startsWith('https://web.cec.gov.tw/'));if(!notice.hidden)notice.href=src;else notice.removeAttribute('href');panel.hidden=false;show();if(focus){byId('selected-county').focus({preventScroll:true});panel.scrollIntoView({block:'nearest'});}}
if(data&&cards.length===22&&cards.every(c=>Array.isArray(data.counties?.[c.dataset.name])&&data.counties[c.dataset.name].length===6&&data.counties[c.dataset.name].every(n=>Number.isInteger(n)&&n>=0))){
 for(const card of cards){const a=card.querySelector('a'),url=a.href;const b=document.createElement('button');b.type='button';b.textContent=card.dataset.name;b.setAttribute('aria-pressed','false');b.setAttribute('aria-controls','county-panel');card.replaceChildren(b);b.addEventListener('click',()=>selectCounty(card,b,url));}
 office.addEventListener('change',show);byId('clear-county').addEventListener('click',()=>clearSelection(true));
}
;document.addEventListener('click',e=>{const b=e.target.closest('.ref-play');if(!b)return;const id=b.dataset.video||'';if(!/^[A-Za-z0-9_-]{11}$/.test(id))return;const f=document.createElement('iframe');f.className='video-frame';f.title=b.dataset.title||'意見發表會';f.src='https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1';f.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';f.allowFullscreen=true;f.referrerPolicy='strict-origin-when-cross-origin';const h=b.closest('.ref-hearing');if(h)h.classList.add('playing');b.parentElement.replaceChildren(f);});
