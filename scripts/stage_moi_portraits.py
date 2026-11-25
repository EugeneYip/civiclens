"""Stage official public-office portrait URLs, without downloading or republishing image bytes."""
import collections, hashlib, json, re, time, urllib.request
from pathlib import Path
from urllib.parse import urljoin,urlparse, urlencode
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
LICENSE="https://www.moi.gov.tw/cp.aspx?n=10954"
BASE="https://www.moi.gov.tw/LocalOfficial.aspx"
def norm(s):return re.sub(r"\s+","",s)
def county_norm(s):return norm(s).replace("台","臺")
def photo_ok(u):
    try:
        p=urlparse(u);return p.scheme=="https" and p.hostname=="ws.moi.gov.tw" and not p.username and not p.password and not p.port and bool(p.path) and not re.search(r"no.?image|default|blank|logo|icon|no.?photo",p.path,re.I)
    except (TypeError,ValueError):return False
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"CivicLens/1.0 (public data attribution research)"}),timeout=25) as r:
        if urlparse(r.geturl()).hostname!="www.moi.gov.tw":raise ValueError("unexpected redirect")
        data=r.read(5*1024*1024+1)
    if len(data)>5*1024*1024:raise ValueError("oversize HTML")
    return data
def parse(raw,url,counties):
    soup=BeautifulSoup(raw,"html.parser");out=[]
    for img in soup.find_all("img"):
        name=norm(img.get("alt",""));src=urljoin(url,img.get("src",""))
        if not name or not photo_ok(src):continue
        # Walk to the smallest card that contains a matching name, a council and a single image.
        for parent in list(img.parents)[:7]:
            if len(parent.find_all("img"))!=1:break
            txt=norm(parent.get_text(" ",strip=True))
            found=[c for c in counties if c+"議會" in county_norm(txt)]
            if len(found)!=1 or name not in txt or not re.search(r"議會(?:代理)?(?:副議長|議長|議員)",txt):continue
            detail=[urljoin(url,a.get("href","")) for a in parent.find_all("a",href=True) if "詳細資訊" in a.get_text(" ",strip=True)]
            if len(detail)!=1:continue
            if urlparse(detail[0]).hostname!="www.moi.gov.tw":continue
            out.append({"name":name,"county":found[0],"src":src,"source":detail[0],"listing":url});break
    return out
def build(rows,roster):
    lookup=collections.defaultdict(list)
    for d in roster:
        for c in d["candidates"]:
            if not c.get("source_conflict"):lookup[(d["county"],norm(c["name"]))].append((d,c))
    grouped=collections.defaultdict(list)
    for row in rows:grouped[(row["county"],row["name"])].append(row)
    records={};skips=collections.Counter()
    for (county,name),group in grouped.items():
        hits=lookup.get((county,name),[])
        if len(hits)!=1:skips["no_unique_candidate"]+=1;continue
        if len({x["src"] for x in group})!=1:skips["conflicting_photo"]+=1;continue
        d,c=hits[0];x=group[0]
        records[c["id"]]={"name":c["name"],"number":c["number"],"county":county,"source_name":x["name"],"src":x["src"],"source":x["source"],"listing":x["listing"],"credit":"內政部地方公職人員資訊專區","license":LICENSE,"role":"2022–2026任期議會公職肖像（非本屆登記照）","status":"official_public_office_photo_reference"}
    return records,dict(skips)
def main():
    gaz=json.loads((ROOT/"data/gazettes.json").read_text());names={county_norm(c["name"]):c["code"] for c in gaz["counties"]}
    roster=[d for f in ("published-roster","national-roster-supplement") for d in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"]]
    rows=[];pages=[];errors=[]
    for typ,n,maxpages in [("KND0001",573,23),("KND0002",574,33)]:
        seen=set()
        # Request larger pages first; if the server still returns 16, keep the original size.
        size=100
        for page in range(1,maxpages+1):
            u=BASE+"?"+urlencode({"TYP":typ,"n":n,"sms":11400,"PageSize":size,"page":page})
            try:
                raw=fetch(u);items=parse(raw,u,names);sig=hashlib.sha256(json.dumps(items and [(x["name"],x["src"]) for x in items],ensure_ascii=False).encode()).hexdigest()
                if not items:errors.append({"type":typ,"page":page,"reason":"no_cards"});continue
                if sig in seen:break
                seen.add(sig)
                if page==1 and len(items)<=16:size=16
                for x in items:x["county"]=names[x["county"]]
                rows.extend(items);pages.append({"type":typ,"page":page,"cards":len(items),"sha256":hashlib.sha256(raw).hexdigest()})
                print(typ,page,len(items),flush=True)
                if page*size >= (356 if typ=="KND0001" else 514):break
            except Exception as e:errors.append({"type":typ,"page":page,"reason":type(e).__name__});print("source_error",typ,page,type(e).__name__,flush=True);break
            time.sleep(0.7)
    records,skips=build(rows,roster)
    stats={"source_cards":len(rows),"pages":len(pages),"matched":len(records),"counties":len({x["county"] for x in records.values()}),"chief":sum("-chief-" in k for k in records),"council":sum("-council-" in k for k in records)}
    if stats["matched"]<10:raise ValueError("insufficient source cards: "+str(errors))
    d={"version":"0.1.21","license":LICENSE,"notice":"內政部公職時期照片連結；姓名及縣市唯一配對，非本屆登記照；未逐張目視核對、未逐檔下載驗證或另行確認第三方權利。","stats":stats,"pages":pages,"errors":errors,"skips":skips,"records":records}
    (ROOT/"data/moi-portrait-references.json").write_text(json.dumps(d,ensure_ascii=False,separators=(",",":"))+"\n")
    print("STATS",json.dumps(stats,ensure_ascii=False),"errors",json.dumps(errors))
if __name__=="__main__":main()
