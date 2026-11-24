'use strict';
const search=document.getElementById('county-search'),region=document.getElementById('region'),count=document.getElementById('count'),empty=document.getElementById('empty');
const cards=[...document.querySelectorAll('.county')],grid=document.querySelector('.county-grid');
const normalize=s=>s.normalize('NFKC').replaceAll('台','臺').trim();
const data=JSON.parse(document.getElementById('elector-data').textContent);
const panel=document.getElementById('county-panel'),office=document.getElementById('office');
const coords={'連江縣':[1,1],'金門縣':[3,1],'澎湖縣':[6,1],'桃園市':[2,2],'新北市':[1,3],'臺北市':[1,2],'基隆市':[1,4],'新竹縣':[3,3],'新竹市':[3,2],'苗栗縣':[4,2],'臺中市':[5,2],'宜蘭縣':[2,4],'花蓮縣':[5,4],'彰化縣':[6,2],'南投縣':[6,3],'雲林縣':[7,2],'嘉義市':[8,2],'嘉義縣':[8,3],'臺南市':[9,2],'高雄市':[9,3],'臺東縣':[8,4],'屏東縣':[10,3]};
let selected=null;
function filter(){const q=normalize(search.value);let visible=0;for(const card of cards){const match=normalize(card.dataset.name).includes(q)&&(!region.value||card.dataset.region===region.value);card.hidden=!match;if(match)visible++}grid.classList.toggle('filtered',Boolean(q||region.value));count.textContent=visible+' / '+cards.length+' 個縣市';empty.hidden=visible!==0;}
function show(){if(!selected)return;const i=Number(office.value),n=data.counties[selected.name][i];document.getElementById('elector-value').textContent=n.toLocaleString('en-US');document.getElementById('elector-label').textContent=i===5?'投票權人人數':'選舉人人數';document.getElementById('elector-category').textContent=data.labels[i]+(n===0?' · 官方統計為 0':'');document.getElementById('elector-source').href=i===5?data.referendum_pdf:data.local_pdf;}
function selectCounty(card,button,url){selected={name:card.dataset.name,button};for(const b of grid.querySelectorAll('button'))b.setAttribute('aria-pressed',String(b===button));document.getElementById('selected-county').textContent=selected.name;document.getElementById('selected-link').href=url;panel.hidden=false;show();}
if(cards.length===22&&cards.every(c=>Array.isArray(data.counties[c.dataset.name])&&data.counties[c.dataset.name].length===6&&coords[c.dataset.name])){
grid.classList.add('schematic');document.getElementById('map-note').hidden=false;
for(const card of cards){const a=card.querySelector('a'),url=a.href;const b=document.createElement('button');b.type='button';b.textContent=card.dataset.name;b.setAttribute('aria-pressed','false');b.setAttribute('aria-controls','county-panel');const [r,c]=coords[card.dataset.name];card.style.gridArea=r+' / '+c;card.replaceChildren(b);b.addEventListener('click',()=>selectCounty(card,b,url));}
office.addEventListener('change',show);document.getElementById('clear-county').addEventListener('click',()=>{const old=selected?.button;selected=null;panel.hidden=true;for(const b of grid.querySelectorAll('button'))b.setAttribute('aria-pressed','false');if(old&&!old.parentElement.hidden)old.focus();else search.focus();});
}
search.addEventListener('input',filter);region.addEventListener('change',filter);document.getElementById('reset').addEventListener('click',()=>{search.value='';region.value='';filter();search.focus()});filter();
