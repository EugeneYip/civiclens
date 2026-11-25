import json, re, unittest
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parents[1]
TOPICS = {"交通", "居住與都市", "教育與青年", "育兒與社福", "醫療與健康", "經濟與就業", "環境與能源", "文化與觀光", "治理與安全"}
SCOPES = {"地方政策主張", "地方政策主張／方向", "議會監督", "涉及中央權責", "涉及跨機關權責"}


class ReviewedCouncilTests(unittest.TestCase):
    def test_reviewed_council_policies(self):
        d = json.loads((ROOT / "data/reviewed-council-policies.json").read_text())
        self.assertEqual(d["version"], "0.1.27")
        roster = {c["id"]: c for f in ("published-roster", "national-roster-supplement") for g in json.loads((ROOT / "data" / (f + ".json")).read_text())["districts"] if g["office"] == "council" for c in g["candidates"]}
        self.assertEqual(len(d["reviewed_counties"]), 22)
        expected = {k for k in roster if k.split("-")[0] in d["reviewed_counties"]}
        self.assertEqual(expected, set(roster))
        self.assertEqual(set(d["records"]), expected)
        ids = set()
        for k, x in d["records"].items():
            self.assertEqual((x["name"], x["number"]), (roster[k]["name"], roster[k]["number"]))
            u = urlparse(x["source"])
            self.assertEqual((u.scheme, u.hostname), ("https", "bulletin.cec.gov.tw"))
            self.assertRegex(x["source"], r"#page=[1-9]\d*$")
            self.assertTrue(any(x["source"].startswith(f["url"] + "#") for f in d["source_files"].values()), k)
            self.assertTrue(x["items"] or "不推定" in x["status"], k)
            for fld in ("education", "experience"):
                if fld in x:
                    self.assertTrue(isinstance(x[fld], list) and all(isinstance(v, str) and v.strip() == v and v for v in x[fld]), k)
                    self.assertLessEqual(len(x[fld]), 8 if fld == "education" else 16, k)
            for i, it in enumerate(x["items"], 1):
                self.assertEqual(it["id"], f"{k}-p{i}")
                self.assertIn(it["topic"], TOPICS)
                self.assertIn(it["scope"], SCOPES)
                self.assertIn("履行尚未查核", it["status"])
                self.assertLessEqual(len(it["summary"]), 45)
                self.assertNotRegex(it["summary"], "[０-９]")
                self.assertNotIn(it["id"], ids)
                ids.add(it["id"])
        for f in d["source_files"].values():
            self.assertRegex(f["sha256"], "^[0-9a-f]{64}$")
        shard_ids = set()
        for f in (ROOT / "data/county").glob("*.json"):
            shard_ids |= set(json.loads(f.read_text())["councilReviews"]["records"])
        self.assertEqual(shard_ids, set(d["records"]))

    def test_no_identification_numbers_published(self):
        # A bulletin may print a certificate number that embeds a national ID; it must be masked.
        for f in sorted((ROOT / "data").rglob("*.json")):
            self.assertIsNone(re.search(r"[A-Z][12][0-9]{8}", f.read_text()), f.name)


if __name__ == "__main__":
    unittest.main()
