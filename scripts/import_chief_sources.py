"""Import links to candidate-origin statements; never republish quotes or third-party prose."""
import collections,gzip,hashlib,io,json,re,urllib.request
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
SHA="39adeee8e8a9ebd0102359090db686e407359359"
REPO=f"https://github.com/skyhong2002/mayor2026/tree/{SHA}"
SLUGS="taipei new-taipei taichung tainan kaohsiung taoyuan hsinchu-county miaoli changhua nantou yunlin chiayi-county pingtung taitung hualien yilan penghu keelung hsinchu-city chiayi-city kinmen lienchiang".split()
TYPES={"政策承諾","公開立場","批評監督","成果陳述","概括願景"}
def safe_url(s):
    try:
        u=urlparse(s)
        return u.scheme=="https" and bool(u.hostname) and not u.username and not u.password and not u.port and "." in u.hostname and len(s)<2048
    except (TypeError,ValueError):return False
def load(slug):
    url=f"https://raw.githubusercontent.com/skyhong2002/mayor2026/{SHA}/data/comparisons/{slug}.json.gz"
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"CivicLens-source-index"}),timeout=30) as r:
        raw=r.read(15*1024*1024+1)
    if len(raw)>15*1024*1024:raise ValueError("compressed size")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f: data=f.read(100*1024*1024+1)
    if len(data)>100*1024*1024:raise ValueError("uncompressed size")
    return json.loads(data),hashlib.sha256(raw).hexdigest()
def extract(data, candidates):
    roster={(r["number"],r["name"]):r for r in candidates if not r.get("source_conflict")}
    matches={}
    for c in data["candidates"]:
        r=roster.get((c["number"],c["name"]))
        if r:matches[c["id"]]=r
    sources={s["id"]:s for s in data["sources"]}
    records={r["id"]:{"name":r["name"],"number":r["number"],"links":[]} for r in matches.values()}
    groups=collections.defaultdict(set)
    count=0
    for c in data["claims"]:
        r=matches.get(c["candidateId"]);s=sources.get(c["sourceId"]);kind=c.get("assertionType")
        if not r or not s or s.get("candidateId")!=c["candidateId"] or kind not in TYPES or not safe_url(s.get("url")):continue
        # Upstream quote must be contiguous in same candidate's source text.
        q=c.get("quote","");raw=s.get("text","")
        norm=lambda v:re.sub(r"\s+","",v)
        if not q or not norm(q) or norm(q) not in norm(raw):continue
        topic=c.get("topic")
        if not isinstance(topic,str) or not re.fullmatch(r"[\u3400-\u9fffA-Za-z、／/與及（）() -]{1,25}",topic):continue
        date=s.get("postedAt") or ""
        if not isinstance(date,str) or not re.match(r"^2026-\d{2}-\d{2}",date):date=""
        groups[(r["id"],s["url"],date[:10],kind)].add(topic)
        count+=1
    for (rid,url,date,kind),topics in sorted(groups.items(),key=lambda kv:(kv[0][2],kv[0][1]),reverse=True):
        records[rid]["links"].append({"url":url,"date":date or None,"type":kind,"topics":sorted(topics)})
    return records,count
def main():
    districts=[d for f in ("published-roster","national-roster-supplement") for d in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] if d["office"]=="chief"]
    by={d["county"]:d["candidates"] for d in districts}
    records={};snapshots={};claims=0;errors=[]
    for i,slug in enumerate(SLUGS,1):
        try:
            x,sha=load(slug);rows,n=extract(x,by[f"{i:02}"]);claims+=n;records.update(rows);snapshots[slug]={"sha256":sha,"matched":len(rows),"claims":n,"analysisAt":x.get("analysisAt")}
        except Exception as e:errors.append({"race":slug,"error":type(e).__name__});print(slug,type(e).__name__,str(e)[:150])
    if len(snapshots)<20 or len(records)<65:raise ValueError("coverage gate "+str(errors))
    stats={"counties":len(snapshots),"matched":len(records),"with_links":sum(bool(x["links"]) for x in records.values()),"links":sum(len(x["links"]) for x in records.values()),"validated_quote_claims":claims,"promise_candidates":sum(any(y["type"]=="政策承諾" for y in x["links"]) for x in records.values())}
    result={"version":"0.1.17","source":{"name":"2026 地方選舉官方來源觀測站","repository":REPO,"method":"候選人姓名、號次、縣市配對；原文引句存在性及來源歸屬檢查，僅發布原文網址、日期、第三方類型及議題。非人工核實承諾或成果。"},"stats":stats,"snapshots":snapshots,"errors":errors,"records":records}
    (ROOT/"data/chief-policy-sources.json").write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n")
    print(json.dumps(stats,ensure_ascii=False))
if __name__=="__main__":main()
