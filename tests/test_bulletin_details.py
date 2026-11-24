import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from extend_bulletin import norm_name,norm_district,policy_details,MEASURES,AMOUNT
class BulletinDetailsTests(unittest.TestCase):
 def test_normalization(self):
  self.assertEqual(norm_name("林某 A．B"),norm_name("林某a‧b"))
  self.assertNotEqual(norm_name("温某"),norm_name("溫某"))
  self.assertNotEqual(norm_name("林某 A"),norm_name("林某"))
  self.assertEqual(norm_district("台北市第０１選舉區"),"臺北市第1選舉區")
 def test_details(self):
  topics=[{"label":"交通","terms":["交通"]},{"label":"社福","terms":["托育"]}]
  self.assertEqual(policy_details("交通改善10公里。托育補助每月3000元。電話12345678元交通補助。",topics),[{"topics":["交通"],"measures":["改善"],"values":["10公里"]},{"topics":["社福"],"measures":["補助"],"values":["3000元"]}])
 def test_data_if_present(self):
  p=ROOT/"data/bulletin-details.json"
  if not p.exists():return
  d=json.loads(p.read_text());f=json.loads((ROOT/"data/bulletin-facts.json").read_text())
  self.assertEqual(set(d["records"]),set(f["records"]))
  self.assertEqual(d["stats"]["matched"],len(d["records"]))
  self.assertEqual(d["stats"]["source_rows"],len(d["records"])+len(d["excluded"]))
  self.assertEqual(d["stats"]["normalized_added"],sum(x["match"]=="format_normalized" for x in d["records"].values()))
  for k,x in d["records"].items():
   r=f["records"][k]
   for a in ("name","number","source","page"): self.assertEqual(x[a],r[a])
   for y in x["policy_details"]:
    self.assertTrue(set(y["measures"])<=set(MEASURES))
    self.assertTrue(all(AMOUNT.fullmatch(v) for v in y["values"]))
