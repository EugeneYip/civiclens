import json, subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_results_snapshot as b  # noqa: E402


def doc(status, rows, valid=None, source="https://info.cec.gov.tw/vote2026/result", at="2026-11-28T19:00:00+08:00"):
    return {"source": source, "published_at": at, "status": status,
            "races": [{"county": "連江縣", "office": "chief", "district": None, "valid_votes": valid, "candidates": rows}]}


class ResultsSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.groups, self.codes = b.roster()

    def test_current_snapshot_has_no_unpublished_counts(self):
        s = json.loads((ROOT / "data/results-snapshot.json").read_text())
        self.assertEqual(s["version"], "0.1.22")
        for gid, r in s["races"].items():
            self.assertIn(gid, self.groups)
            self.assertTrue(b.official(r["source"]))

    def test_final_race_is_strictly_checked(self):
        ok = [{"number": 1, "name": "王忠銘", "votes": 10, "elected": False}, {"number": 2, "name": "曹爾元", "votes": 20, "elected": True}]
        races = b.build_races(doc("final", ok, 30), self.groups, self.codes)
        self.assertEqual([c["id"] for c in races["22-chief"]["candidates"]], ["22-chief-1", "22-chief-2"])
        for bad, why in (
            (doc("final", ok, 31), "votes must add up"),
            (doc("final", ok[:1], 10), "every candidate"),
            (doc("final", [dict(ok[0], name="王忠明"), ok[1]], 30), "name must match"),
            (doc("final", [dict(ok[0], elected=None), ok[1]], 30), "elected flag"),
            (doc("final", [dict(ok[0], elected=True), ok[1]], 30), "seat count"),
            (doc("final", ok, 30, source="https://example.com/x"), "official host"),
            (doc("final", ok, 30, at="2026-11-28T15:00:00+08:00"), "after polls close"),
            (doc("preliminary", ok, None), "no winners before final"),
        ):
            with self.assertRaises(b.ResultError, msg=why):
                b.build_races(bad, self.groups, self.codes)

    def test_preliminary_and_merge_never_downgrade(self):
        pre = b.build_races(doc("preliminary", [{"number": 1, "name": "王忠銘", "votes": 5}], None, at="2026-11-28T20:00:00+08:00"), self.groups, self.codes)
        fin = b.build_races(doc("final", [{"number": 1, "name": "王忠銘", "votes": 10, "elected": False}, {"number": 2, "name": "曹爾元", "votes": 20, "elected": True}], 30), self.groups, self.codes)
        self.assertEqual(b.merge(fin, pre)["22-chief"]["status"], "final")

    def test_browser_validator_accepts_builder_output(self):
        fin = b.build_races(doc("final", [{"number": 1, "name": "王忠銘", "votes": 10, "elected": False}, {"number": 2, "name": "曹爾元", "votes": 20, "elected": True}], 30), self.groups, self.codes)
        g = self.groups["22-chief"]
        js = ("const r=require(%s);const ok=r.validateRace(%s,%s,1,Date.parse('2026-11-29T00:00:00+08:00'));process.exit(ok?0:1)"
              % (json.dumps(str(ROOT / "scripts/results.js")), json.dumps(fin["22-chief"], ensure_ascii=False), json.dumps(g, ensure_ascii=False)))
        self.assertEqual(subprocess.run(["node", "-e", js]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
