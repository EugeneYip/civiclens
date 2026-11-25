import json,unittest
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
class ReviewedPilotTests(unittest.TestCase):
 def test_pilot(self):
  d=json.loads((ROOT/"data/reviewed-policy-pilot.json").read_text())
  roster={x["id"]:x for f in ("published-roster","national-roster-supplement") for g in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] if g["office"]=="chief" and g["county"] in ("01","02","03","04","05","06","07","09","11","12","15","19") for x in g["candidates"]}
  self.assertEqual(set(d["records"]),set(roster))
  self.assertEqual(d["version"],"0.1.24")
  ids=set()
  for k,x in d["records"].items():
   self.assertEqual((x["name"],x["number"]),(roster[k]["name"],roster[k]["number"]))
   self.assertIn(urlparse(x["source"]).hostname,("bulletin.cec.gov.tw","eebulletin.cec.gov.tw"))
   self.assertTrue(x["source"].endswith("#page=1"))
   for i in x["items"]:
    self.assertIn("履行尚未查核",i["status"])
    self.assertNotIn(i["id"],ids);ids.add(i["id"])
  self.assertGreaterEqual(len(ids),75)
  self.assertEqual(len(d["reviewed_counties"]),12)
 def test_historical(self):
  x=json.loads((ROOT/"data/historical-review.json").read_text())
  self.assertEqual(len(x["counties"]),6)
  self.assertEqual(x["term"],"2022–2026")
