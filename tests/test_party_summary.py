import json, subprocess, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


class PartySummaryTests(unittest.TestCase):
    def test_summary_is_current_and_consistent(self):
        subprocess.run([sys.executable, str(ROOT / "scripts/build_party_summary.py"), "--check"], check=True)
        d = json.loads((ROOT / "data/party-summary.json").read_text())
        self.assertEqual(d["version"], "0.1.25")
        groups = [g for f in ("published-roster", "national-roster-supplement") for g in json.loads((ROOT / "data" / (f + ".json")).read_text())["districts"]]
        ids = {c["id"]: g for g in groups for c in g["candidates"]}
        self.assertEqual(set(d["candidates"]), set(ids))
        self.assertEqual(d["seats"]["chief"] + d["seats"]["council"], 941)
        for office, total in (("chief", 81), ("council", 1493)):
            n = d["national"][office]
            self.assertEqual(n["candidates"], total)
            self.assertEqual(sum(x["candidates"] for x in n["parties"]), total)
            self.assertEqual(sum(n["tiers"].values()), total)
            self.assertEqual(sum(c[office]["candidates"] for c in d["counties"].values()), total)
        for cid, (party, tier) in d["candidates"].items():
            self.assertIn(tier, d["tier_labels"])
            self.assertEqual(party is None, tier == "pending", cid)
            if party is not None:
                self.assertNotIn(" ", party)
                self.assertNotIn(party, ("無黨籍", "未經政黨推薦"))
        roster = {c["id"]: c for g in groups for c in g["candidates"]}
        for cid, c in roster.items():
            if c.get("party") is not None:
                self.assertEqual(d["candidates"][cid][1], "official")


if __name__ == "__main__":
    unittest.main()
