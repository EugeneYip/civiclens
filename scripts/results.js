"use strict";
const opening=Date.parse("2026-11-28T16:00:00+08:00");
const officialHosts=new Set(["www.cec.gov.tw","web.cec.gov.tw","info.cec.gov.tw","db.cec.gov.tw","vote.cec.gov.tw","data.cec.gov.tw"]);
function resultPhase(now){return now<opening?"投票截止後開放官方開票查詢｜11/28 16:00（臺灣時間）":"已達預定開票時間；請查閱中選會實際發布狀態。"}
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
if(typeof module!=="undefined")module.exports={resultPhase,officialSource,validateRace,opening};
if(typeof document!=="undefined")(()=>{
 const $=id=>document.getElementById(id),county=$("result-county"),office=$("result-office"),district=$("result-district"),rows=$("result-rows"),status=$("result-data-status"),summary=$("result-summary"),src=$("result-source"),headline=$("result-heading");
 const fmt=new Intl.NumberFormat("zh-TW");let data=null,refreshing=false;
 function update(){ $("phase").textContent=resultPhase(Date.now());if(data)render() }
 async function refresh(){if(!data||refreshing||Date.now()<opening)return;refreshing=true;try{const s=await load("results-snapshot",true);if(s?.version==="0.1.22"&&s.election_date==="2026-11-28"&&s.races&&typeof s.races==="object"&&!Array.isArray(s.races)){const valid={};for(const [k,r] of Object.entries(s.races)){const g=data.groups.find(x=>x.id===k);if(!g)continue;const seats=g.office==="chief"?1:data.districts.counties.find(x=>x.code===g.county)?.districts.find(d=>d.id===k)?.seats;if(validateRace(r,g,seats,Date.now()))valid[k]=r}const previous=data.snapshot.races;for(const [k,r] of Object.entries(previous)){if(!valid[k]||Date.parse(valid[k].published_at)<Date.parse(r.published_at)||r.status==="final"&&valid[k].status!=="final")valid[k]=r}data.snapshot={...s,races:valid};render();$("result-refresh-status").textContent="已檢查本站快照："+new Date().toLocaleTimeString("zh-TW",{timeZone:"Asia/Taipei",hour12:false})+"（臺灣時間）"}else throw Error("snapshot")}catch{$("result-refresh-status").textContent="更新未成功，保留先前有效資料。"}finally{refreshing=false}}
 function el(tag,txt){const x=document.createElement(tag);if(txt!==undefined)x.textContent=txt;return x}
 function opt(select,items){select.replaceChildren(...items.map(([k,v])=>{const x=el("option",v);x.value=k;return x}));select.disabled=!items.length}
 function setDistrict(preferred){const c=data.districts.counties.find(x=>x.code===county.value);opt(district,c.districts.map(d=>[String(d.number),"第"+d.number+"選區｜"+d.scope]));if(c.districts.some(d=>String(d.number)===preferred))district.value=preferred;$("result-district-label").hidden=office.value!=="council"}
 function render(){
  const c=data.election.counties.find(x=>x.code===county.value),role=office.value,number=Number(district.value);
  const group=data.groups.find(g=>g.county===c.code&&g.office===role&&(role==="chief"||g.number===number));
  const seats=role==="chief"?1:data.districts.counties.find(x=>x.code===c.code).districts.find(d=>d.number===number)?.seats;
  headline.textContent=c.name+(role==="chief"?"｜縣市長":"｜議員第"+number+"選區");
  summary.textContent=group?group.candidates.length+" 位候選人 · "+seats+" 席（選前名冊）":"尚無本選區候選人名冊";
  rows.replaceChildren();src.hidden=true;src.removeAttribute("href");
  const race=group&&validateRace(data.snapshot.races[group.id],group,seats,Date.now());
  status.textContent=race?(race.status==="final"?"正式公告結果":"官方開票資料（尚非正式公告）")+"｜"+new Date(race.published_at).toLocaleString("zh-TW",{timeZone:"Asia/Taipei",hour12:false})+" 臺灣時間":"尚未取得可驗證官方票數；下方僅為選前候選人名冊。";
  if(race){src.hidden=false;src.href=race.source}
  const votes=new Map((race?.candidates||[]).map(x=>[x.id,x]));
  for(const c of group?.candidates||[]){
   const tr=el("tr"),v=votes.get(c.id),name=el("td"),a=el("a",c.name);
   a.href="./?county="+county.value+"&office="+role+(role==="council"?"&district="+number:"")+"&candidate="+encodeURIComponent(c.id)+"#directory";name.append(a);
   tr.append(el("td",String(c.number)),name,el("td",v?fmt.format(v.votes):"—"),el("td",v&&race.status==="final"?(v.elected?"當選":"未當選"):"—"));rows.append(tr)
  }
  const u=new URL(location.href);u.searchParams.set("county",county.value);u.searchParams.set("office",role);if(role==="council")u.searchParams.set("district",district.value);else u.searchParams.delete("district");history.replaceState(null,"",u.pathname+u.search+u.hash)
 }
 const load=async (p,fresh=false)=>{const r=await fetch("data/"+p+".json",fresh?{cache:"no-cache"}:{});if(!r.ok)throw Error(p);return r.json()};
 Promise.all([load("election"),load("council-districts"),load("published-roster"),load("national-roster-supplement"),load("results-snapshot").catch(()=>({version:"0.1.22",races:{}}))]).then(([e,d,a,b,s])=>{
  const groups=[...a.districts,...b.districts];
  if(e.counties.length!==22||d.district_count!==221||groups.length!==243||new Set(groups.map(g=>g.id)).size!==243)throw Error("roster validation");
  data={election:e,districts:d,groups,snapshot:s?.version==="0.1.22"&&s.races&&typeof s.races==="object"?s:{races:{}}};
  opt(county,e.counties.map(x=>[x.code,x.name]));const q=new URLSearchParams(location.search);if(e.counties.some(c=>c.code===q.get("county")))county.value=q.get("county");office.disabled=false;if(q.get("office")==="council")office.value="council";setDistrict(q.get("district"));render();refresh();
 }).catch(()=>{status.textContent="名冊載入失敗，請使用中選會官方入口。";county.disabled=office.disabled=district.disabled=true});
 county.addEventListener("change",()=>{setDistrict();render()});office.addEventListener("change",()=>{setDistrict(district.value);render()});district.addEventListener("change",render);
 $("result-refresh").addEventListener("click",()=>{if(Date.now()<opening){$("result-refresh-status").textContent="尚未達預定開票時間。";return}refresh()});update();setInterval(()=>{update();if(!document.hidden)refresh()},60000);document.addEventListener("visibilitychange",()=>{if(!document.hidden){update();refresh()}});
})();
