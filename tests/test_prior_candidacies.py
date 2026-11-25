import json, re, unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


class PriorCandidacyTests(unittest.TestCase):
    def test_links(self):
        d = json.loads((ROOT / "data/prior-candidacies-2022.json").read_text())
        self.assertEqual(d["version"], "0.1.44")
        groups = [g for f in ("published-roster", "national-roster-supplement") for g in json.loads((ROOT / "data" / (f + ".json")).read_text())["districts"]]
        county = {c["id"]: g["county"] for g in groups for c in g["candidates"]}
        names = {c["code"]: c["name"] for c in json.loads((ROOT / "data/election.json").read_text())["counties"]}
        files = {f["url"] for f in d["source"]["files"]}
        self.assertGreater(d["stats"]["linked"], 800)
        self.assertEqual(d["stats"]["linked"], len(d["records"]))
        for k, r in d["records"].items():
            self.assertIn(k, county)
            self.assertTrue(r["race"].startswith(names[county[k]]), k)  # same county only
            self.assertIn(r["source"], files)
            self.assertEqual(urlparse(r["source"]).hostname, "db.cec.gov.tw")
            self.assertIsInstance(r["elected"], bool)
            self.assertTrue(isinstance(r["votes"], int) and r["votes"] >= 0)
        self.assertIn("14-council-1-16", {x["id"] for x in d["rejected"]})  # same name, different birth year
        self.assertNotIn("14-council-1-16", d["records"])
        shard = set()
        for f in (ROOT / "data/county").glob("*.json"):
            shard |= set(json.loads(f.read_text())["prior"]["records"])
        self.assertEqual(shard, set(d["records"]))


if __name__ == "__main__":
    unittest.main()
