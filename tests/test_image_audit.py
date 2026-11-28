import json,unittest,sys,datetime as dt
from pathlib import Path
R=Path(__file__).resolve().parents[1]/"data"
def load(n):return json.loads((R/(n+".json")).read_text())
class ImageAuditTests(unittest.TestCase):
 def test_audit_inventory(self):
  m=load("media-assets");e=load("candidate-enrichment");o=load("moi-portrait-references");a=load("image-availability-audit")
  inv={**{"portrait:"+k:v["src"] for k,v in {**o["records"],**e["photos"],**m["photos"]}.items()},**{"party:"+k:v["src"] for k,v in m["parties"].items()}}
  self.assertEqual(len(inv),a["inventory"])
  self.assertEqual(a["checked"],len(a["records"]))
  self.assertEqual(sum(a["counts"].values()),a["checked"])
  for k,x in a["records"].items():self.assertEqual(x["url"],inv[k])
  self.assertEqual(len({o["records"][k[9:]]["county"] for k in a["records"] if k.startswith("portrait:") and k[9:] in o["records"]}),22)
 def test_results_snapshot(self):
  # The published snapshot is produced by scripts/build_results_snapshot.py from the CEC count pages.
  sys.path.insert(0,str(R.parent/"scripts"))
  import build_results_snapshot as b
  groups,codes=b.roster();s=load("results-snapshot")
  self.assertEqual((s["version"],s["election_date"]),("0.1.22","2026-11-28"))
  self.assertEqual(s["status"],("final" if s["races"] and all(r["status"]=="final" for r in s["races"].values()) and len(s["races"])==len(groups) else "partial") if s["races"] else "not_published")
  for k,r in s["races"].items():
   g=groups[k];by={c["id"]:c for c in g["candidates"]}
   self.assertTrue(b.official(r["source"]),k);self.assertGreaterEqual(dt.datetime.fromisoformat(r["published_at"]),b.OPENING)
   total=0
   for v in r["candidates"]:
    c=by[v["id"]];self.assertEqual((v["name"],v["number"]),(c["name"],c["number"]));self.assertIs(type(v["votes"]),int);total+=v["votes"]
    self.assertEqual("elected" in v,r["status"]=="final",k)
   if r["valid_votes"] is not None:self.assertGreaterEqual(r["valid_votes"],total,k)
   if "stations" in r:self.assertLessEqual(r["stations"]["reported"],r["stations"]["total"],k)
