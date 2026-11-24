import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReviewedPilotTests(unittest.TestCase):
 def test_pilot(self):
  d=json.loads((ROOT/"data/reviewed-policy-pilot.json").read_text())
  r=json.loads((ROOT/"data/published-roster.json").read_text())
  roster={x["id"]:x for g in r["districts"] if g["office"]=="chief" for x in g["candidates"]}
  self.assertEqual(set(d["records"]),set(roster))
  self.assertEqual(sum(len(x["items"]) for x in d["records"].values()),9)
  for k,x in d["records"].items():
   self.assertEqual(x["name"],roster[k]["name"])
   self.assertTrue(x["source"].startswith("https://bulletin.cec.gov.tw/"))
   self.assertTrue(x["source"].endswith("#page=1"))
   for i in x["items"]:self.assertIn("履行尚未查核",i["status"])
 def test_historical(self):
  x=json.loads((ROOT/"data/historical-review.json").read_text())
  self.assertEqual(len(x["counties"]),6)
  self.assertEqual(x["term"],"2022–2026")
