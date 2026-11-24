import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from derive_bulletin import facts, EDUCATION, CAREER, official_url
class BulletinFactsTests(unittest.TestCase):
 def test_filters(self):
  self.assertEqual(facts(["國立臺灣大學碩士","住址某大學","大學電話12345678","大學畢業。其他"],EDUCATION),["國立臺灣大學碩士"])
  self.assertEqual(facts(["市議員","市議員涉案","不相關"],CAREER),["市議員"])
 def test_generated_data_if_present(self):
  p=ROOT/"data/bulletin-facts.json"
  if not p.exists(): return
  d=json.loads(p.read_text())
  rows={r["id"]:r for f in ("published-roster","national-roster-supplement") for g in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] for r in g["candidates"]}
  self.assertEqual(d["version"],"0.1.15")
  self.assertEqual(len(d["records"]),d["stats"]["matched"])
  self.assertGreaterEqual(len(d["records"]),1000)
  terms={x["label"]:set(x["terms"]) for x in json.loads((ROOT/"data/policy-topics.json").read_text())["topics"]}
  for k,x in d["records"].items():
   self.assertEqual(set(x),{"name","number","source","page","education","career","party","topics","text_available","status"})
   self.assertEqual(x["name"],rows[k]["name"])
   self.assertEqual(x["number"],rows[k]["number"])
   self.assertFalse(rows[k].get("source_conflict"))
   self.assertTrue(official_url(x["source"]))
   self.assertGreater(x["page"],0)
   self.assertEqual(x["education"],facts(x["education"],EDUCATION))
   self.assertEqual(x["career"],facts(x["career"],CAREER))
   for t,v in x["topics"].items(): self.assertTrue(set(v)<=terms[t])
