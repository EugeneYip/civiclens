'use strict';
const search=document.getElementById('county-search'),region=document.getElementById('region'),count=document.getElementById('count'),empty=document.getElementById('empty');
const cards=[...document.querySelectorAll('.county')];
const normalize=s=>s.normalize('NFKC').replaceAll('台','臺').trim();
function filter(){const q=normalize(search.value);let visible=0;for(const card of cards){const match=normalize(card.dataset.name).includes(q)&&(!region.value||card.dataset.region===region.value);card.hidden=!match;if(match)visible++}count.textContent=`${visible} / ${cards.length} 個縣市`;empty.hidden=visible!==0;}
search.addEventListener('input',filter);region.addEventListener('change',filter);document.getElementById('reset').addEventListener('click',()=>{search.value='';region.value='';filter();search.focus()});filter();
