import json,unittest
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
 def test_results_empty(self):
  a=load("results-snapshot");self.assertEqual(a["status"],"not_published");self.assertEqual(a["races"],{})
