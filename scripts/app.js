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
function tick(){const t=countdownState(Date.now());byId('countdown-label').textContent={date:'距離投票日期還有',opening:'距離投票開始還有',closing:'距離投票截止還有',ended:'2026 年 11 月 28 日'}[t.phase];byId('countdown-clock').hidden=t.phase==='ended';byId('countdown-ended').hidden=t.phase!=='ended';const bring=byId('bring');if(bring)bring.hidden=t.phase==='ended';const quick=byId('quick');if(quick)quick.hidden=t.phase==='ended';for(const k of ['days','hours','minutes','seconds'])byId(k).textContent=String(t[k]).padStart(2,'0');}
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
// Official referendum count (data/referendum-result.json, built from the CEC count site).
(()=>{const box=document.getElementById('ref-live');if(!box)return;const opening=Date.parse('2026-11-28T16:00:00+08:00'),nf=new Intl.NumberFormat('zh-TW');
 const ok=r=>{try{const u=new URL(r.source);const ints=['agree','disagree','valid','invalid','ballots','electorate_reported','electorate','votes_needed'].every(k=>Number.isSafeInteger(r[k])&&r[k]>=0),t=Date.parse(r.published_at);
  return u.protocol==='https:'&&u.hostname==='vote.cec.gov.tw'&&ints&&r.agree+r.disagree===r.valid&&r.valid+r.invalid===r.ballots&&r.stations&&r.stations.reported<=r.stations.total&&r.stations.total>0&&t>=opening&&t<=Date.now()+300000&&r.votes_needed===5000959&&r.electorate===20003835}catch{return false}};
 const pct=(a,b)=>b>0?(a/b*100).toFixed(2)+'%':'—';
 const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
 function bar(label,n,of){const row=el('div','rl-row');const top=el('div','rl-top');top.append(el('span','rl-label',label),el('span','rl-num',nf.format(n)+'（'+pct(n,of)+'）'));const track=el('div','rl-track');const fill=el('span','rl-fill');fill.style.width=of>0?Math.min(100,n/of*100)+'%':'0';track.append(fill);row.append(top,track);return row}
 function draw(r){const done=r.status==='complete'&&r.stations.reported===r.stations.total;box.replaceChildren();
  const title=el('div','rl-title');const h=el('h3',null,'全國性公投第22案');const more=el('a','small','主文與說明 ↓');more.href='#referendum';title.append(h,more);
  const q=el('p','rl-q','你是否支持政府使用「核電」振興經濟，以廢除「非核家園」的能源政策？');
  const head=el('div','rl-head');head.append(el('strong',null,done?'開票完成':'開票中'),el('span','small','已送投票所 '+nf.format(r.stations.reported)+'／'+nf.format(r.stations.total)+'｜更新 '+new Date(r.published_at).toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false,month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})+' 臺灣時間'));
  box.append(title,q,head,bar('同意',r.agree,r.valid),bar('不同意',r.disagree,r.valid));
  const th=el('div','rl-row rl-threshold');const top=el('div','rl-top');top.append(el('span','rl-label','同意票／通過門檻'),el('span','rl-num',nf.format(r.agree)+'／'+nf.format(r.votes_needed)));const track=el('div','rl-track');const fill=el('span','rl-fill');fill.style.width=Math.min(100,r.agree/r.votes_needed*100)+'%';track.append(fill);th.append(top,track);box.append(th);
  box.append(el('p','small','有效票 '+nf.format(r.valid)+'・無效票 '+nf.format(r.invalid)+'・'+(done?'投票率 ':'已完成投票所投票率 ')+pct(r.ballots,r.electorate_reported)));
  const note=done&&typeof r.meets_threshold==='boolean'?(r.meets_threshold?'依開票結果，同意票多於不同意票且達投票權人總數四分之一，符合公民投票法第29條通過條件；正式結果以中選會公告為準。':'依開票結果，未同時符合「同意票多於不同意票」及「達投票權人總數四分之一」，依公民投票法第29條為不通過；正式結果以中選會公告為準。'):'開票完成前不判定通過與否。數字取自中選會計票網站，最新以中選會為準。';
  const p=el('p','small rl-note',note+' ');const a=el('a',null,'中選會原文 ↗');a.href=r.source;a.target='_blank';a.rel='noopener noreferrer';p.append(a);box.append(p);box.hidden=false}
 function load(){if(Date.now()<opening)return;fetch('data/referendum-result.json?t='+Date.now(),{cache:'no-store'}).then(x=>x.ok?x.json():null).then(r=>{if(r&&ok(r))draw(r)}).catch(()=>{})}
 load();setInterval(()=>{if(!document.hidden)load()},120000);})();
// Home-page county map of mayor/magistrate races (data/results-map.json + data/taiwan-counties-map.json).
(()=>{const host=document.getElementById('results-map');if(!host)return;const opening=Date.parse('2026-11-28T16:00:00+08:00'),nf=new Intl.NumberFormat('zh-TW'),NS='http://www.w3.org/2000/svg';
 const PC={'中國國民黨':'#2f5ea8','民主進步黨':'#2e9a5a','台灣民眾黨':'#23a3a6','無':'#7b848b'},OTHER='#9c7f55',col=p=>PC[p]||OTHER,pname=p=>p==='無'?'無推薦政黨':p;
 const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e},sv=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e};
 const time=s=>new Date(s).toLocaleString('zh-TW',{timeZone:'Asia/Taipei',hour12:false,month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});
 const okSrc=s=>{try{const u=new URL(s);return u.protocol==='https:'&&u.hostname==='vote.cec.gov.tw'}catch{return false}};
 function word(c){if(!c.leader)return c.status==='none'?'尚無票數':'同票';return c.status==='final'?'當選':c.status==='all_reported'?'預計當選':'領先'}
 function draw(geo,m){host.replaceChildren();const rows=m.counties.filter(c=>c.status==='none'||(okSrc(c.source)&&Date.parse(c.published_at)>=opening));
  const allFinal=rows.length===22&&rows.every(c=>c.status==='final'),allIn=rows.length===22&&rows.every(c=>c.status==='final'||c.status==='all_reported');
  const ttl=el('h3','rm-title','縣市長');const head=el('div','rl-head');head.append(el('strong',null,allFinal?'開票完成':allIn?'全部投票所開票完成':'開票中'),el('span','small','已送投票所 '+nf.format(m.stations.reported)+'／'+nf.format(m.stations.total)+'｜更新 '+time(m.published_at)+' 臺灣時間'));
  const grid=el('div','rm-grid'),fig=el('figure','rm-map'),svg=sv('svg',{viewBox:geo.viewBox,role:'img','aria-labelledby':'rm-title'});svg.append(Object.assign(sv('title',{id:'rm-title'}),{textContent:'各縣市長目前得票最高者地圖（文字版見右側清單）'}));
  for(const b of geo.insets){const [x,y,w,h]=b.box;svg.append(sv('rect',{x,y,width:w,height:h,rx:3,class:'rm-inset'}));const t=sv('text',{x:x+4,y:y+10,class:'rm-inset-label'});t.textContent=geo.counties[b.code].name;svg.append(t)}
  const by=new Map(rows.map(c=>[c.cec,c]));
  for(const [code,g] of Object.entries(geo.counties)){const c=by.get(code),a=sv('a',{href:c?'results.html?county='+c.code+'&office=chief':'results.html'}),p=sv('path',{d:g.d,class:'rm-county'});
   if(c&&c.leader){const f=col(c.leader.party);p.style.fill=f;if(c.status==='counting')p.style.fillOpacity='.5';if(['09007','09020','10016'].includes(code)){p.style.stroke=f;p.style.strokeWidth='1.6';p.style.strokeOpacity=c.status==='counting'?'.5':'1'}}
   const tt=sv('title');tt.textContent=g.name+'：'+(c&&c.leader?c.leader.name+'（'+pname(c.leader.party)+'）'+word(c)+' '+c.leader.share.toFixed(2)+'%':'尚無票數')+(c&&c.stations?.total?'，已送投票所 '+c.stations.reported+'／'+c.stations.total:'');a.append(tt,p);svg.append(a)}
  fig.append(svg);
  const counts=new Map();for(const c of rows)if(c.leader){const k=c.leader.party;counts.set(k,(counts.get(k)||0)+1)}
  const lg=el('ul','rm-legend');for(const [k,n] of [...counts].sort((a,b)=>b[1]-a[1])){const li=el('li');const sw=el('span','rm-sw');sw.style.background=col(k);li.append(sw,document.createTextNode(pname(k)+' '+n));lg.append(li)}
  const key=el('p','small rm-key',allIn&&!allFinal?'各縣市依全部投票所得票數之得票最高者；中選會尚未標示當選。':'淺色：開票中目前領先；深色：投票所全數送達之得票最高者'+(rows.some(c=>c.status==='final')?'；標示「當選」者為中選會已標示當選':'')+'。');
  fig.append(lg,key);
  const list=el('ol','rm-list');for(const c of rows){const li=el('li'),a=el('a');a.href='results.html?county='+c.code+'&office=chief';const nm=el('span','rm-cn',c.name);
   const who=el('span','rm-who');if(c.leader){const d=el('span','rm-dot');d.style.background=col(c.leader.party);who.append(d,document.createTextNode(c.leader.name));const pt=el('span','rm-party',pname(c.leader.party));who.append(pt)}else who.append(document.createTextNode(word(c)));
   const st=el('span','rm-st',c.leader?c.leader.share.toFixed(1)+'%':''),pr=el('span','rm-pr',(c.leader?word(c):'')+(c.stations?.total?(c.leader?'・':'')+(c.status==='counting'?'開票 '+Math.floor(c.stations.reported/c.stations.total*100)+'%':'投票所全數送達'):''));a.append(nm,st,who,pr);li.append(a);list.append(li)}
  grid.append(fig,list);
  const note=el('p','small rm-note','依中選會計票網站各縣市長得票數；中選會未標示當選前，僅顯示目前得票最高者，不代表當選。當選以中選會公告為準。地圖依內政部國土測繪中心縣市界線（經 taiwan-atlas 轉製）簡化繪製，金門縣、連江縣以插圖表示。');
  host.append(ttl,head,grid,note)}
 function load(){if(Date.now()<opening)return;Promise.all(['data/taiwan-counties-map.json','data/results-map.json?t='+Date.now()].map(u=>fetch(u,{cache:u.includes('?t=')?'no-store':'default'}).then(r=>r.ok?r.json():Promise.reject()))).then(([g,m])=>{if(Object.keys(g.counties||{}).length===22&&Array.isArray(m.counties)&&m.counties.length===22)draw(g,m)}).catch(()=>{})}
 load();setInterval(()=>{if(!document.hidden)load()},180000);})();
