import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]/"data"
def load(f): return json.loads((R/(f+".json")).read_text())
rows={r["id"]:r for f in ("published-roster","national-roster-supplement") for d in load(f)["districts"] for r in d["candidates"]}
e=load("candidate-enrichment"); c=load("candidate-careers"); p=load("candidate-parties"); b=load("bulletin-facts"); m=load("media-assets")
def present(k,r,old=True):
 x=e["records"].get(k,{})
 y=b["records"].get(k,{}) if not old else {}
 return {"education":bool(r.get("education") or r.get("supplemental_education") or x.get("education") or y.get("education")),
 "career":bool(r.get("experience") or c["records"].get(k,{}).get("items") or y.get("career")),
 "party":bool(r.get("party") is not None or r.get("registration_party") is not None or p["records"].get(k) or y.get("party")),
 "policy":bool(r.get("platform") or x.get("policy") or y.get("topics")),
 "policy_text_source":bool(y.get("text_available"))}
extra=load("bulletin-details")
print(json.dumps({"before":{f:sum(present(k,r,True)[f] for k,r in rows.items()) for f in present(next(iter(rows)),next(iter(rows.values())))}, "after":{f:sum(present(k,r,False)[f] for k,r in rows.items()) for f in present(next(iter(rows)),next(iter(rows.values())))}, "bulletin":b["stats"],"details":extra["stats"]},ensure_ascii=False))

moi=load("moi-portrait-references"); images=load("image-availability-audit")
portraits=set(m["photos"])|set(e["photos"])|set(moi["records"])
print(json.dumps({"portraits":len(portraits),"emblems":len(m["parties"]),"image_audit":{"checked":images["checked"],"inventory":images["inventory"],"counts":images["counts"]}},ensure_ascii=False))
