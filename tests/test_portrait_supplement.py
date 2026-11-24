import json,unittest
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
class PortraitSupplementTests(unittest.TestCase):
 def test_portraits(self):
  data=json.loads((ROOT/"data/media-assets.json").read_text())
  roster={r["id"]:r for f in ("published-roster","national-roster-supplement") for d in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] for r in d["candidates"]}
  new={k:v for k,v in data["photos"].items() if v.get("name")}
  self.assertEqual(len(new),7)
  for k,v in new.items():
   self.assertEqual(v["name"],roster[k]["name"])
   self.assertIn(urlparse(v["src"]).hostname,("thumb.wikimedia.org","upload.wikimedia.org"))
   self.assertEqual(urlparse(v["source"]).hostname,"commons.wikimedia.org")
   self.assertIn("非本屆登記照",v["role"])
   self.assertTrue(v["credit"] and v["rights"])
