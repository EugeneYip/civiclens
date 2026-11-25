import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage_moi_portraits import parse,build,photo_ok
class MoiPortraitTests(unittest.TestCase):
 def test_parse(self):
  h=b'<div><img alt="\xe7\x8e\x8b\xe7\x94\xb2" src="https://ws.moi.gov.tw/p.jpg"><p>\xe7\x8e\x8b\xe7\x94\xb2 \xe8\x87\xba\xe5\x8c\x97\xe5\xb8\x82\xe8\xad\xb0\xe6\x9c\x83\xe8\xad\xb0\xe5\x93\xa1</p><a href="/a">\xe8\xa9\xb3\xe7\xb4\xb0\xe8\xb3\x87\xe8\xa8\x8a</a></div>'
  self.assertEqual(len(parse(h,"https://www.moi.gov.tw/LocalOfficial.aspx",["臺北市"])),1)
  self.assertFalse(photo_ok("https://example.com/p.jpg"))
 def test_generated(self):
  p=ROOT/"data/moi-portrait-references.json"
  if not p.exists():return
  d=json.loads(p.read_text());r={x["id"]:(g,x) for f in ("published-roster","national-roster-supplement") for g in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] for x in g["candidates"]}
  self.assertEqual(d["stats"]["matched"],len(d["records"]))
  for k,x in d["records"].items():
   g,y=r[k];self.assertEqual((x["name"],x["number"],x["county"]),(y["name"],y["number"],g["county"]))
   self.assertEqual(x["source_name"],"".join(y["name"].split()));self.assertTrue(photo_ok(x["src"]));self.assertIn("非本屆登記照",x["role"])
