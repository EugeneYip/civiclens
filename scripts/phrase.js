// Phrase-aware line breaking for Traditional Chinese.
// Browsers wrap CJK text between any two characters, which splits words such as 精神 or 非核家園
// across lines. This script segments text into words with Intl.Segmenter and inserts <wbr> only at
// word boundaries; CSS (html.phrase) then sets word-break:keep-all so lines break only there, at
// spaces, or (as a last resort) wherever overflow-wrap allows. Text content is unchanged: <wbr> adds
// no characters, so copying, searching and screen readers see the original text.
(()=>{
  if(typeof Intl==="undefined"||typeof Intl.Segmenter!=="function"||!window.MutationObserver)return;
  const seg=new Intl.Segmenter("zh-Hant",{granularity:"word"});
  const HAN=/[㐀-鿿豈-﫿]/, OPEN=/[「『（〔【《〈(“‘]/, CLOSE=/[，。、；：」』）〕】》〉！？…,.;:!?)”’]/;
  const SKIP=new Set(["SCRIPT","STYLE","TEXTAREA","OPTION","OPTGROUP","SELECT","INPUT","CODE","PRE","svg","TITLE","NOSCRIPT"]);
  const done=new WeakSet();
  const LAT=/[A-Za-z]/;
  const breakable=(a,b)=>!CLOSE.test(b)&&!OPEN.test(a)&&(HAN.test(a)||CLOSE.test(a)||(LAT.test(a)&&HAN.test(b)))&&(HAN.test(b)||OPEN.test(b)||(LAT.test(b)&&HAN.test(a)));
  function skipped(n){for(let p=n.parentNode;p&&p.nodeType===1;p=p.parentNode)if(SKIP.has(p.nodeName)||p.isContentEditable)return true;return false}
  // Split a text node into word-sized runs separated by <wbr>. Inside a flex or grid container each
  // child would become its own item, so the runs are then kept together in one inline <span>. Text
  // styled not to wrap is left alone, because <wbr> would still add a break opportunity there.
  function pieces(t){
    if(done.has(t))return null;done.add(t);
    const s=t.nodeValue;if(!s||s.length<4||!HAN.test(s)||!t.parentNode||skipped(t))return null;
    const parts=[];let cur="";
    for(const {segment} of seg.segment(s)){if(cur&&breakable(cur[cur.length-1],segment[0])){parts.push(cur);cur=segment}else cur+=segment}
    parts.push(cur);return parts.length<2?null:parts;
  }
  function apply(t,parts,boxed){
    if(!t.parentNode)return;
    const f=boxed?document.createElement("span"):document.createDocumentFragment();
    parts.forEach((p,i)=>{if(i)f.appendChild(document.createElement("wbr"));const n=document.createTextNode(p);done.add(n);f.appendChild(n)});
    t.parentNode.replaceChild(f,t);
  }
  function process(nodes){
    const jobs=[],flex=new Map();
    for(const t of nodes){const parts=pieces(t);if(!parts)continue;const p=t.parentNode;
      if(!flex.has(p)){const cs=getComputedStyle(p),ws=cs.textWrapMode||cs.whiteSpace||"";flex.set(p,/nowrap|^pre$/.test(ws)?null:/flex|grid/.test(cs.display))}
      const boxed=flex.get(p);if(boxed!==null)jobs.push([t,parts,boxed])}
    for(const [t,parts,boxed] of jobs)apply(t,parts,boxed);
  }
  function collect(root,list){
    if(root.nodeType===3){if(!done.has(root))list.push(root);return}
    if(root.nodeType!==1||SKIP.has(root.nodeName))return;
    const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    while(w.nextNode())if(!done.has(w.currentNode))list.push(w.currentNode);
  }
  document.documentElement.classList.add("phrase");
  function start(){
    const first=[];collect(document.body,first);process(first);
    new MutationObserver(rs=>{const list=[];for(const r of rs){if(r.type==="characterData"){done.delete(r.target);list.push(r.target)}else r.addedNodes.forEach(n=>collect(n,list))}if(list.length)process(list)}).observe(document.body,{childList:true,subtree:true,characterData:true});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start);else start();
})();
