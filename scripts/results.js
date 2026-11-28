"use strict";
const opening=Date.parse("2026-11-28T16:00:00+08:00");
const officialHosts=new Set(["www.cec.gov.tw","web.cec.gov.tw","info.cec.gov.tw","db.cec.gov.tw","vote.cec.gov.tw","data.cec.gov.tw"]);
function resultPhase(now){return now<opening?"投票截止後開放官方開票查詢｜11/28 16:00（臺灣時間）":"開票中：票數取自中選會計票網站，正式當選以中選會審定公告為準。"}
function officialSource(s){try{const u=new URL(s);return u.protocol==="https:"&&officialHosts.has(u.hostname)&&!u.username&&!u.password&&!u.port}catch{return false}}
function validCount(n){return Number.isSafeInteger(n)&&n>=0}
function validateRace(r,group,seats,now){
 if(!r||!["preliminary","final"].includes(r.status)||!officialSource(r.source)||typeof r.published_at!=="string"||!/(?:Z|[+-]\d\d:\d\d)$/.test(r.published_at))return null;
 const stamp=Date.parse(r.published_at);if(!Number.isFinite(stamp)||stamp<opening||stamp>now||now<opening)return null;
 if(!Array.isArray(r.candidates)||!validCount(seats)||seats<1)return null;
 const by=new Map(group.candidates.map(c=>[c.id,c])),seen=new Set();
 let known=0,winners=0;
 for(const v of r.candidates){
  const c=by.get(v.id);if(!c||seen.has(v.id)||v.name!==c.name||v.number!==c.number||!validCount(v.votes))return null;
  if(r.status==="final"){if(typeof v.elected!=="boolean")return null;winners+=Number(v.elected)}
  else if(v.elected!==undefined&&v.elected!==null)return null;
  seen.add(v.id);known+=v.votes;if(!Number.isSafeInteger(known))return null;
 }
 if(r.valid_votes!==null&&r.valid_votes!==undefined&&(!validCount(r.valid_votes)||known>r.valid_votes))return null;
 if(r.status==="final"&&(seen.size!==by.size||winners!==seats||!validCount(r.valid_votes)||known!==r.valid_votes))return null;
 return r;
}
function partyName(p){return p==="無"?"無推薦政黨":p==null||p==="待核"?"政黨欄位待核":p}
function partySeats(groups,races,seatsFor,partyMap,now){
 const out={races:groups.length,seats:0,finalRaces:0,finalSeats:0,byParty:new Map()};
 for(const g of groups){
  const seats=seatsFor(g);if(validCount(seats))out.seats+=seats;
  const r=validateRace(races?.[g.id],g,seats,now);if(!r||r.status!=="final")continue;
  out.finalRaces++;out.finalSeats+=seats;
  for(const v of r.candidates)if(v.elected){const k=partyName(partyMap?.[v.id]?.[0]);out.byParty.set(k,(out.byParty.get(k)||0)+1)}
 }
 return out;
}
function priorSeats(h,scope,role,code){
 const m=new Map();if(!h)return m;
 const add=(p,n)=>{const k=partyName(p);m.set(k,(m.get(k)||0)+n)};
 if(scope==="all"){for(const x of role==="chief"?h.national.chief_seats:h.national.council_parties)add(x.party,x.seats)}
 else{const c=h.counties[code];if(!c)return m;if(role==="chief")for(const x of c.chief.candidates){if(x.elected)add(x.party,1)}else for(const x of c.council.parties)add(x.party,x.seats)}
 return m;
}
if(typeof module!=="undefined")module.exports={resultPhase,officialSource,validateRace,opening,partySeats,partyName,priorSeats};
if(typeof document!=="undefined")(()=>{
 const $=id=>document.getElementById(id),partyScope=$("party-scope"),partyOffice=$("party-office"),county=$("result-county"),office=$("result-office"),district=$("result-district"),rows=$("result-rows"),status=$("result-data-status"),summary=$("result-summary"),src=$("result-source"),headline=$("result-heading");
 const fmt=new Intl.NumberFormat("zh-TW");let data=null,refreshing=false;
 function update(){ $("phase").textContent=resultPhase(Date.now());if(data)render() }
 async function refresh(){if(!data||refreshing||Date.now()<opening)return;refreshing=true;try{const s=await load("results-snapshot",true);if(s?.version==="0.1.22"&&s.election_date==="2026-11-28"&&s.races&&typeof s.races==="object"&&!Array.isArray(s.races)){const valid={};for(const [k,r] of Object.entries(s.races)){const g=data.groups.find(x=>x.id===k);if(!g)continue;const seats=g.office==="chief"?1:data.districts.counties.find(x=>x.code===g.county)?.districts.find(d=>d.id===k)?.seats;if(validateRace(r,g,seats,Date.now()))valid[k]=r}const previous=data.snapshot.races;for(const [k,r] of Object.entries(previous)){if(!valid[k]||Date.parse(valid[k].published_at)<Date.parse(r.published_at)||r.status==="final"&&valid[k].status!=="final")valid[k]=r}data.snapshot={...s,races:valid};render();$("result-refresh-status").textContent="已檢查本站快照："+new Date().toLocaleTimeString("zh-TW",{timeZone:"Asia/Taipei",hour12:false})+"（臺灣時間）"}else throw Error("snapshot")}catch{$("result-refresh-status").textContent="更新未成功，保留先前有效資料。"}finally{refreshing=false}}
 function el(tag,txt){const x=document.createElement(tag);if(txt!==undefined)x.textContent=txt;return x}
 function opt(select,items){select.replaceChildren(...items.map(([k,v])=>{const x=el("option",v);x.value=k;return x}));select.disabled=!items.length}
 function setDistrict(preferred){const c=data.districts.counties.find(x=>x.code===county.value);opt(district,c.districts.map(d=>[String(d.number),"第"+d.number+"選區｜"+d.scope]));if(c.districts.some(d=>String(d.number)===preferred))district.value=preferred;$("result-district-label").hidden=office.value!=="council"}
 function seatsFor(g){return g.office==="chief"?1:data.districts.counties.find(x=>x.code===g.county)?.districts.find(d=>d.id===g.id)?.seats}
 function renderParty(){
  const body=$("party-rows"),st=$("party-status"),tiers=$("party-tiers");body.replaceChildren();
  if(!data?.parties){st.textContent="政黨統計未能載入；不影響上方選前名冊。";partyScope.disabled=partyOffice.disabled=true;return}
  const scope=partyScope.value,role=partyOffice.value,c=data.election.counties.find(x=>x.code===county.value);
  const t=scope==="all"?data.parties.national[role]:data.parties.counties[c.code]?.[role];if(!t)return;
  const groups=data.groups.filter(g=>g.office===role&&(scope==="all"||g.county===c.code));
  const s=partySeats(groups,data.snapshot.races,seatsFor,data.parties.candidates,Date.now());
  const label=(scope==="all"?"全國":c.name)+"｜"+(role==="chief"?"縣市長":"縣市議員");
  $("party-heading").textContent="政黨提名與當選席次｜"+label;
  st.textContent=fmt.format(t.candidates)+" 位候選人 · 應選 "+fmt.format(s.seats)+" 席 · "+(s.finalRaces?"已開票完成並標示當選 "+s.finalRaces+"／"+s.races+" 場（"+s.finalSeats+" 席）":"尚無開票完成之選區，當選席次不推估");
  const prior=priorSeats(data.history,scope,role,c.code);
  for(const x of t.parties){
   const tr=el("tr"),share=el("td"),bar=el("span",undefined),pct=x.candidates/t.candidates*100,name=partyName(x.party);
   bar.className="party-bar";bar.style.width=Math.max(pct,1).toFixed(1)+"%";share.append(bar,el("span",pct.toFixed(1)+"%"));
   tr.append(el("th",name),el("td",fmt.format(x.candidates)),share,el("td",s.finalRaces?fmt.format(s.byParty.get(name)||0):"—"),el("td",prior.size?fmt.format(prior.get(name)||0):"—"));tr.firstChild.scope="row";body.append(tr);prior.delete(name)
  }
  for(const [name,n] of prior){if(!n)continue;const tr=el("tr");tr.append(el("th",name),el("td","0"),el("td","—"),el("td",s.finalRaces?fmt.format(s.byParty.get(name)||0):"—"),el("td",fmt.format(n)));tr.firstChild.scope="row";body.append(tr)}
  const L=data.parties.tier_labels;tiers.textContent="政黨欄位來源："+Object.entries(t.tiers).filter(([,n])=>n).map(([k,n])=>L[k]+" "+n+" 人").join("、")+"。";
 }
 function renderHistory(c,role){
  const body=$("history-rows"),head=$("history-head"),st=$("history-status");body.replaceChildren();head.replaceChildren();body.closest("table").className="result-table history-table "+role;
  const h=data.history?.counties[c.code];$("history-heading").textContent="前屆結果參考｜111年"+c.name+(role==="chief"?"縣市長":"議員（全縣市）");
  if(!h){st.textContent="前屆結果資料未能載入；請使用中選會選舉資料庫。";return}
  const th=t=>{const x=el("th",t);x.scope="col";return x};
  if(role==="chief"){const x=h.chief;head.append(th("號次"),th("候選人"),th("推薦政黨"),th("得票"),th("得票率"),th("結果"));
   st.textContent=x.election+"（"+x.vote_date+"）｜有效票 "+fmt.format(x.valid_votes)+"｜投票率 "+x.turnout_percent+"%";
   for(const v of x.candidates){const tr=el("tr");tr.append(el("td",String(v.number)),el("td",v.name+(v.incumbent?"（時任）":"")),el("td",partyName(v.party)),el("td",fmt.format(v.votes)),el("td",v.percent.toFixed(2)+"%"),el("td",v.elected?"當選":"未當選"));body.append(tr)}}
  else{const x=h.council;head.append(th("政黨"),th("候選人"),th("得票"),th("當選席次"));
   st.textContent="111年議員選舉（含"+x.types.join("、")+"選區）｜"+x.districts+" 個選區、"+fmt.format(x.candidates)+" 位候選人、"+x.seats+" 席；本屆應選 "+data.districts.counties.find(d=>d.code===c.code).seats+" 席，選區劃分可能不同。";
   for(const v of x.parties){const tr=el("tr");tr.append(el("td",partyName(v.party)),el("td",fmt.format(v.candidates)),el("td",fmt.format(v.votes)),el("td",fmt.format(v.seats)));body.append(tr)}}
 }
 function render(){
  const c=data.election.counties.find(x=>x.code===county.value),role=office.value,number=Number(district.value);
  const group=data.groups.find(g=>g.county===c.code&&g.office===role&&(role==="chief"||g.number===number));
  const seats=role==="chief"?1:data.districts.counties.find(x=>x.code===c.code).districts.find(d=>d.number===number)?.seats;
  headline.textContent=c.name+(role==="chief"?"｜縣市長":"｜議員第"+number+"選區");
  summary.textContent=group?group.candidates.length+" 位候選人 · "+seats+" 席（選前名冊）":"尚無本選區候選人名冊";
  rows.replaceChildren();src.hidden=true;src.removeAttribute("href");
  const race=group&&validateRace(data.snapshot.races[group.id],group,seats,Date.now());
  const st=race?.stations,stOk=st&&validCount(st.reported)&&validCount(st.total)&&st.total>0&&st.reported<=st.total;
  const allIn=stOk&&st.reported===st.total;
  status.textContent=race?(race.status==="final"?"開票完成（中選會計票網站已標示當選；正式當選以審定公告為準）":allIn?"投票所已全部送達（中選會尚未標示當選；本站不自行判定，當選以中選會公告為準）":"開票中（中選會計票網站累計，尚非最終結果）")+"｜"+(stOk?"已送投票所 "+fmt.format(st.reported)+"／"+fmt.format(st.total)+"｜":"")+"更新 "+new Date(race.published_at).toLocaleString("zh-TW",{timeZone:"Asia/Taipei",hour12:false,month:"numeric",day:"numeric",hour:"2-digit",minute:"2-digit"})+" 臺灣時間":"尚未取得可驗證官方票數；下方僅為選前候選人名冊。";
  if(race){src.hidden=false;src.href=race.source}
  const votes=new Map((race?.candidates||[]).map(x=>[x.id,x]));
  for(const c of group?.candidates||[]){
   const tr=el("tr"),v=votes.get(c.id),name=el("td"),a=el("a",c.name);
   a.href="./?county="+county.value+"&office="+role+(role==="council"?"&district="+number:"")+"&candidate="+encodeURIComponent(c.id)+"#directory";name.append(a);if(v?.source_name&&v.source_name!==c.name){const sn=el("span","計票網站作「"+v.source_name+"」");sn.className="party-sub";name.append(sn)}const pt=data.parties?.candidates?.[c.id]?.[0];if(pt!==undefined){const ps=el("span",partyName(pt));ps.className="party-sub";name.append(ps)}
   const pct=v&&validCount(race.valid_votes)&&race.valid_votes>0?(v.votes/race.valid_votes*100).toFixed(2)+"%":"—";
   tr.append(el("td",String(c.number)),name,el("td",v?fmt.format(v.votes):"—"),el("td",pct),el("td",v&&race.status==="final"?(v.elected?"當選":"未當選"):"—"));if(v&&race.status==="final"&&v.elected)tr.className="elected";rows.append(tr)
  }
  const u=new URL(location.href);u.searchParams.set("county",county.value);u.searchParams.set("office",role);if(role==="council")u.searchParams.set("district",district.value);else u.searchParams.delete("district");history.replaceState(null,"",u.pathname+u.search+u.hash);renderParty();renderHistory(c,role)
 }
 const load=async (p,fresh=false)=>{const r=await fetch("data/"+p+".json",fresh?{cache:"no-cache"}:{});if(!r.ok)throw Error(p);return r.json()};
 Promise.all([load("election"),load("council-districts"),load("published-roster"),load("national-roster-supplement"),load("results-snapshot").catch(()=>({version:"0.1.22",races:{}})),load("party-summary").catch(()=>null),load("historical-results-2022").catch(()=>null)]).then(([e,d,a,b,s,p,h])=>{
  const groups=[...a.districts,...b.districts];
  if(e.counties.length!==22||d.district_count!==221||groups.length!==243||new Set(groups.map(g=>g.id)).size!==243)throw Error("roster validation");
  const partiesOk=p?.version==="0.1.26"&&p.national&&p.counties&&p.candidates&&groups.every(g=>g.candidates.every(c=>Array.isArray(p.candidates[c.id])));
  const historyOk=h?.version==="0.1.25"&&h.national&&e.counties.every(c=>h.counties?.[c.code]?.chief&&h.counties[c.code].council);
  data={election:e,districts:d,groups,parties:partiesOk?p:null,history:historyOk?h:null,snapshot:s?.version==="0.1.22"&&s.races&&typeof s.races==="object"?s:{races:{}}};
  opt(county,e.counties.map(x=>[x.code,x.name]));const q=new URLSearchParams(location.search);if(e.counties.some(c=>c.code===q.get("county")))county.value=q.get("county");office.disabled=false;if(q.get("office")==="council")office.value="council";setDistrict(q.get("district"));render();refresh();
 }).catch(()=>{status.textContent="名冊載入失敗，請使用中選會官方入口。";county.disabled=office.disabled=district.disabled=true});
 county.addEventListener("change",()=>{setDistrict();render()});office.addEventListener("change",()=>{setDistrict(district.value);render()});district.addEventListener("change",render);partyScope.addEventListener("change",renderParty);partyOffice.addEventListener("change",renderParty);
 $("result-refresh").addEventListener("click",()=>{if(Date.now()<opening){$("result-refresh-status").textContent="尚未達預定開票時間。";return}refresh()});update();setInterval(()=>{update();if(!document.hidden)refresh()},60000);document.addEventListener("visibilitychange",()=>{if(!document.hidden){update();refresh()}});
})();
