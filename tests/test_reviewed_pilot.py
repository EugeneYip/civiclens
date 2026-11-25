import json,re,unittest
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
TOPICS={"交通","居住與都市","教育與青年","育兒與社福","醫療與健康","經濟與就業","環境與能源","文化與觀光","治理與安全","社福"}
class ReviewedPilotTests(unittest.TestCase):
 def test_pilot(self):
  d=json.loads((ROOT/"data/reviewed-policy-pilot.json").read_text())
  roster={x["id"]:x for f in ("published-roster","national-roster-supplement") for g in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] if g["office"]=="chief" for x in g["candidates"]}
  self.assertEqual(set(d["records"]),set(roster))
  self.assertEqual(d["version"],"0.1.25")
  ids=set()
  for k,x in d["records"].items():
   self.assertEqual((x["name"],x["number"]),(roster[k]["name"],roster[k]["number"]))
   self.assertIn(urlparse(x["source"]).hostname,("bulletin.cec.gov.tw","eebulletin.cec.gov.tw"))
   self.assertRegex(x["source"],r"#page=[1-9]\d*$")
   self.assertTrue(x["items"] or "不推定" in x["status"] or "未能" in x["status"],k)
   for i in x["items"]:
    self.assertIn("履行尚未查核",i["status"])
    self.assertTrue(i["id"].startswith(k+"-p"))
    self.assertIn(i["topic"],TOPICS)
    self.assertLessEqual(len(i["summary"]),60)
    self.assertNotRegex(i["summary"],"[０-９]")
    self.assertNotIn(i["id"],ids);ids.add(i["id"])
  self.assertGreaterEqual(len(ids),190)
  self.assertEqual(len(d["reviewed_counties"]),22)
  self.assertEqual(len(d["records"]),81)
  for c,f in d["source_files"].items():
   self.assertRegex(f["sha256"],"^[0-9a-f]{64}$")
   self.assertTrue(all(x["source"].startswith(f["url"]+"#") for k,x in d["records"].items() if k[:2]==c))
 def test_historical(self):
  x=json.loads((ROOT/"data/historical-review.json").read_text())
  self.assertEqual(len(x["counties"]),6)
  self.assertEqual(x["term"],"2022–2026")
