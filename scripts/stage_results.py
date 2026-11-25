"""Stage manually reviewed CEC result transcriptions. Not a live API adapter.
No network, no automatic publication. Input CSV is a CivicLens interchange format.
"""
import argparse,csv,datetime as dt,hashlib,json,re,sys
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
OPEN=dt.datetime.fromisoformat("2026-11-28T16:00:00+08:00")
HOSTS={"www.cec.gov.tw","web.cec.gov.tw","info.cec.gov.tw","db.cec.gov.tw","vote.cec.gov.tw","data.cec.gov.tw"}
FIELDS=["county","office","district","number","name","votes","elected","valid_votes"]
MAX=10*1024*1024
def load(n):return json.loads((ROOT/"data"/(n+".json")).read_text())
def source_ok(u):
    p=urlparse(u)
    return p.scheme=="https" and p.hostname in HOSTS and not p.username and not p.password and not p.port and bool(p.path) and p.path!="/"
def timestamp(s):
    t=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("timezone required")
    return t
def count(s):
    if not re.fullmatch(r"0|[1-9][0-9]{0,12}",s):raise ValueError("invalid integer: "+repr(s))
    return int(s)
def maps():
    groups={g["id"]:g for f in ("published-roster","national-roster-supplement") for g in load(f)["districts"]}
    seats={g["id"]:1 for g in groups.values() if g["office"]=="chief"}
    seats.update({d["id"]:d["seats"] for c in load("council-districts")["counties"] for d in c["districts"]})
    if len(groups)!=243 or set(groups)!=set(seats):raise ValueError("roster scope mismatch")
    return groups,seats
def build(rows,groups,seats,source,published,status,sha,now):
    if status not in ("preliminary","final") or not source_ok(source):raise ValueError("invalid status/source")
    t=timestamp(published)
    if not OPEN<=t<=now or now<OPEN:raise ValueError("outside official release window")
    if not re.fullmatch(r"[a-f0-9]{64}",sha):raise ValueError("source hash required")
    races={}
    for row in rows:
        if set(row)!=set(FIELDS) or any(not isinstance(v,str) for v in row.values()):raise ValueError("invalid CSV columns")
        county,office,dist=row["county"],row["office"],row["district"]
        if not re.fullmatch(r"0[1-9]|1[0-9]|2[0-2]",county) or office not in ("chief","council"):raise ValueError("bad race key")
        if office=="chief" and dist!="":raise ValueError("chief district must be blank")
        if office=="council" and count(dist)<1:raise ValueError("invalid district")
        k=county+"-"+office+("-"+dist if office=="council" else "")
        g=groups.get(k)
        if not g:raise ValueError("unknown race: "+k)
        number=count(row["number"]);matches=[c for c in g["candidates"] if c["number"]==number and c["name"]==row["name"] and not c.get("source_conflict")]
        if len(matches)!=1:raise ValueError("candidate identity conflict: "+k+" "+row["name"])
        c=matches[0];valid=count(row["valid_votes"]) if row["valid_votes"] else None
        if status=="final" and row["elected"] not in ("true","false"):raise ValueError("official elected field required")
        if status=="preliminary" and row["elected"]:raise ValueError("preliminary cannot mark winners")
        v={"id":c["id"],"name":c["name"],"number":number,"votes":count(row["votes"]),"elected":row["elected"]=="true" if status=="final" else None}
        race=races.setdefault(k,{"status":status,"source":source,"published_at":published,"source_sha256":sha,"valid_votes":valid,"candidates":[]})
        if race["valid_votes"]!=valid or any(x["id"]==v["id"] for x in race["candidates"]):raise ValueError("inconsistent totals or duplicate candidate: "+k)
        race["candidates"].append(v)
    if not races:raise ValueError("no records")
    for k,r in races.items():
        total=sum(v["votes"] for v in r["candidates"])
        if r["valid_votes"] is not None and total>r["valid_votes"]:raise ValueError("votes exceed valid votes: "+k)
        if status=="final" and (len(r["candidates"])!=len(groups[k]["candidates"]) or r["valid_votes"]!=total or sum(v["elected"] for v in r["candidates"])!=seats[k]):raise ValueError("final race reconciliation failed: "+k)
        r["candidates"].sort(key=lambda x:x["number"])
    return races
def merge(old,new):
    out=dict(old)
    for k,r in new.items():
        prev=out.get(k)
        if prev and timestamp(r["published_at"])<timestamp(prev["published_at"]):raise ValueError("stale snapshot: "+k)
        if prev and prev["status"]=="final" and prev!=r:raise ValueError("final result correction needs separate review: "+k)
        if prev and timestamp(r["published_at"])==timestamp(prev["published_at"]) and prev!=r:raise ValueError("conflicting same-time result: "+k)
        out[k]=r
    return out
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv",type=Path);p.add_argument("--source-file",type=Path,required=True);p.add_argument("--source-url",required=True);p.add_argument("--published-at",required=True);p.add_argument("--status",choices=["preliminary","final"],required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--reviewed-transcription",action="store_true",required=True)
    a=p.parse_args()
    if a.output.resolve()==(ROOT/"data/results-snapshot.json").resolve():raise ValueError("stage outside published path; review diff before publication")
    if any(f.stat().st_size>MAX for f in (a.csv,a.source_file)):raise ValueError("input too large")
    sha=hashlib.sha256(a.source_file.read_bytes()).hexdigest()
    with a.csv.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=FIELDS:raise ValueError("exact interchange header required")
        rows=list(reader)
    g,s=maps();new=build(rows,g,s,a.source_url,a.published_at,a.status,sha,dt.datetime.now(dt.timezone.utc))
    old=load("results-snapshot");races=merge(old["races"],new)
    out={**old,"status":"published_data_available","races":races,"notice":"人工核對之中選會資料轉錄；非即時 API。每選區保留原始來源及發布時間。"}
    a.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"staged_races":len(new),"total_races":len(races),"source_sha256":sha}))
if __name__=="__main__":main()
