import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from import_chief_sources import extract,safe_url,TYPES
class ChiefPolicySourcesTests(unittest.TestCase):
 def test_source_attribution(self):
  r=[{"id":"01-chief-1","name":"甲","number":1}]
  data={"candidates":[{"id":"a","name":"甲","number":1}],"sources":[{"id":"s","candidateId":"a","url":"https://example.org/post","text":"我將增加交通建設","postedAt":"2026-11-01"}],"claims":[{"candidateId":"a","sourceId":"s","assertionType":"政策承諾","topic":"交通","quote":"增加交通建設"},{"candidateId":"a","sourceId":"s","assertionType":"政策承諾","topic":"交通","quote":"不存在"}]}
  x,n=extract(data,r)
  self.assertEqual(n,1)
  self.assertEqual(len(x["01-chief-1"]["links"]),1)
  self.assertFalse(safe_url("javascript:alert(1)"))
 def test_data_if_present(self):
  p=ROOT/"data/chief-policy-sources.json"
  if not p.exists():return
  d=json.loads(p.read_text())
  self.assertGreaterEqual(d["stats"]["counties"],20)
  self.assertEqual(d["stats"]["matched"],len(d["records"]))
  self.assertEqual(d["stats"]["links"],sum(len(x["links"]) for x in d["records"].values()))
  roster={r["id"]:r for f in ("published-roster","national-roster-supplement") for g in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] for r in g["candidates"]}
  for k,x in d["records"].items():
   self.assertEqual((x["name"],x["number"]),(roster[k]["name"],roster[k]["number"]))
   for y in x["links"]:
    self.assertEqual(set(y),{"url","date","type","topics"})
    self.assertTrue(safe_url(y["url"]))
    self.assertIn(y["type"],TYPES)
