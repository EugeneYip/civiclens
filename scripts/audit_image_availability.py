"""Bounded image availability audit: no image bytes retained, no face recognition."""
import argparse,collections,datetime,hashlib,io,json,time,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
HOSTS={"ws.moi.gov.tw","upload.wikimedia.org","thumb.wikimedia.org","raw.githubusercontent.com"}
MAX=6*1024*1024
Image.MAX_IMAGE_PIXELS=25000000
def load(name):return json.loads((ROOT/"data"/(name+".json")).read_text())
def inventory():
    m=load("media-assets");e=load("candidate-enrichment");o=load("moi-portrait-references")
    return {**{"portrait:"+k:v["src"] for k,v in {**o["records"],**e["photos"],**m["photos"]}.items()},**{"party:"+k:v["src"] for k,v in m["parties"].items()}}
def sample(inv,all_items=False):
    if all_items:return dict(sorted(inv.items()))
    moi=load("moi-portrait-references")["records"]; chosen={}
    for k,u in sorted(inv.items()):
        if not u.startswith("https://ws.moi.gov.tw/"):chosen[k]=u
    for county in sorted({v["county"] for v in moi.values()}):
        k=next(k for k in sorted(moi) if moi[k]["county"]==county)
        chosen["portrait:"+k]=inv["portrait:"+k]
    return chosen
def safe(u):
    p=urlparse(u)
    return p.scheme=="https" and p.hostname in HOSTS and not p.username and not p.password and not p.port
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None
def check(url):
    if not safe(url):return {"state":"invalid_url"}
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"CivicLens/1.0 (public image link audit; https://civiclens.eugeneyip.net/)","Accept":"image/*"})
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=10) as response:
            mime=response.headers.get_content_type();raw=response.read(MAX+1)
        if len(raw)>MAX:return {"state":"size_limit","mime":mime}
        if mime=="image/svg+xml":
            import xml.etree.ElementTree as ET
            if not ET.fromstring(raw).tag.endswith("}svg"):return {"state":"invalid_image","mime":mime}
            return {"state":"readable_svg","mime":mime,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
        if not mime.startswith("image/"):return {"state":"not_image","mime":mime}
        with Image.open(io.BytesIO(raw)) as im:
            width,height=im.size;im.verify()
        return {"state":"readable_raster","mime":mime,"width":width,"height":height,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
    except urllib.error.HTTPError as e:
        return {"state":"http_error","http":e.code}
    except Exception as e:
        return {"state":"unconfirmed","error":type(e).__name__}
def run_group(items):
    out={}
    for k,u in items:
        out[k]={"url":u,**check(u)}
        time.sleep(1)
    return out
def main():
    p=argparse.ArgumentParser();p.add_argument("--all",action="store_true");a=p.parse_args()
    inv=inventory();chosen=sample(inv,a.all);groups=collections.defaultdict(list)
    # One request at a time per host, no retry or external redirects.
    for k,u in chosen.items():groups[urlparse(u).hostname].append((k,u))
    rows={}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(run_group,groups.values()):rows.update(result)
    counts=collections.Counter(x["state"] for x in rows.values())
    result={"version":"0.1.22","checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"all" if a.all else "all non-MOI sources and one MOI candidate per county","inventory":len(inv),"checked":len(rows),"counts":dict(counts),"records":rows,"notice":"HTTP及影像格式檢查，不代表人像身分、授權或前端載入確認。未檢查不代表失效。"}
    (ROOT/"data/image-availability-audit.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("AUDIT",json.dumps({k:v for k,v in result.items() if k!="records"},ensure_ascii=False))
if __name__=="__main__":main()
