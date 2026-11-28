import json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(n):
    return json.loads((ROOT / "data" / n).read_text())


class ResultsMapTests(unittest.TestCase):
    def test_geometry(self):
        g = load("taiwan-counties-map.json")
        self.assertEqual(len(g["counties"]), 22)
        self.assertRegex(g["source"], r"^https://cdn\.jsdelivr\.net/npm/taiwan-atlas@2021\.9\.20/counties-10t\.json$")
        for code, c in g["counties"].items():
            self.assertRegex(code, r"^\d{5}$")
            self.assertTrue(c["d"].startswith("M") and c["d"].endswith("Z"), c["name"])

    def test_leaders_follow_official_counts(self):
        m, snap, parties = load("results-map.json"), load("results-snapshot.json"), load("party-summary.json")["candidates"]
        names = {c["code"]: c["name"] for c in load("election.json")["counties"]}
        self.assertEqual([c["code"] for c in m["counties"]], list(names))
        for c in m["counties"]:
            r = snap["races"].get(c["code"] + "-chief")
            if not r:
                self.assertEqual(c["status"], "none"); continue
            self.assertEqual(c["source"], r["source"])
            votes = sorted((v["votes"] for v in r["candidates"]), reverse=True)
            if c["status"] == "final":
                self.assertTrue(r["status"] == "final" and c["leader"]["id"] in {v["id"] for v in r["candidates"] if v["elected"]})
            elif c["leader"]:
                self.assertEqual(c["leader"]["votes"], votes[0]); self.assertGreater(votes[0], votes[1] if len(votes) > 1 else -1)
                self.assertEqual(c["leader"]["party"], parties[c["leader"]["id"]][0])
                self.assertEqual(c["status"] == "all_reported", r["stations"]["reported"] == r["stations"]["total"])
            else:
                self.assertTrue(sum(votes) == 0 or votes[0] == votes[1])


if __name__ == "__main__":
    unittest.main()
