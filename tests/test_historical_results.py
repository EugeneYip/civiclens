import json, unittest
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parents[1]


class HistoricalResultsTests(unittest.TestCase):
    def setUp(self):
        self.d = json.loads((ROOT / "data/historical-results-2022.json").read_text())

    def test_official_sources(self):
        files = self.d["source"]["files"]
        self.assertGreaterEqual(len(files), 50)
        for f in files:
            u = urlparse(f["url"])
            self.assertEqual((u.scheme, u.hostname), ("https", "db.cec.gov.tw"))
            self.assertTrue(u.path.startswith("/static/elections/data/"))
            self.assertRegex(f["sha256"], "^[0-9a-f]{64}$")

    def test_chief_results_reconcile(self):
        counties = json.loads((ROOT / "data/election.json").read_text())["counties"]
        self.assertEqual(set(self.d["counties"]), {c["code"] for c in counties})
        winners = {}
        for code, c in self.d["counties"].items():
            x = c["chief"]
            self.assertEqual(sum(v["elected"] for v in x["candidates"]), 1, code)
            self.assertEqual(sum(v["votes"] for v in x["candidates"]), x["valid_votes"], code)
            self.assertEqual(x["valid_votes"] + x["invalid_votes"], x["total_votes"], code)
            self.assertEqual([v["number"] for v in x["candidates"]], sorted(v["number"] for v in x["candidates"]))
            top = max(x["candidates"], key=lambda v: v["votes"])
            self.assertTrue(top["elected"], code)
            winners[code] = top["party"]
        self.assertEqual(self.d["counties"]["20"]["chief"]["vote_date"], "2022-12-18")
        self.assertEqual(sum(x["seats"] for x in self.d["national"]["chief_seats"]), 22)

    def test_council_totals(self):
        seats = sum(c["council"]["seats"] for c in self.d["counties"].values())
        self.assertEqual(seats, self.d["national"]["council_seats"])
        self.assertEqual(seats, 910)
        self.assertEqual(sum(x["seats"] for x in self.d["national"]["council_parties"]), 910)
        for code, c in self.d["counties"].items():
            x = c["council"]
            self.assertEqual(sum(p["seats"] for p in x["parties"]), x["seats"], code)
            self.assertEqual(sum(p["candidates"] for p in x["parties"]), x["candidates"], code)
            self.assertEqual(sum(p["votes"] for p in x["parties"]), x["valid_votes"], code)
            self.assertIn("區域", x["types"])


if __name__ == "__main__":
    unittest.main()
