import json, math, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReferendumTests(unittest.TestCase):
    def setUp(self):
        self.r = json.loads((ROOT / "data/referendum.json").read_text())

    def test_question_and_case(self):
        self.assertEqual(self.r["case"], 22)
        self.assertEqual(self.r["question"], "你是否支持政府使用「核電」振興經濟，以廢除「非核家園」的能源政策？")
        self.assertEqual(self.r["proposer"]["body"], "立法院")

    def test_threshold_matches_official_electorate(self):
        electors = json.loads((ROOT / "data/electors.json").read_text())
        n = electors["totals"][electors["labels"].index("全國性公投第22案")]
        self.assertEqual(self.r["electorate"]["count"], n)
        self.assertEqual(self.r["threshold"]["votes_needed"], math.ceil(n / 4))
        self.assertIn("四分之一以上", self.r["threshold"]["text"])

    def test_reason_is_clean(self):
        paras = self.r["reason"]["paragraphs"]
        self.assertGreaterEqual(len(paras), 20)
        for p in paras:
            self.assertIn(p["kind"], ("heading", "item", "para"))
            self.assertIsNone(re.search(r"[。：」]\d$", p["text"]), p["text"][-20:])  # no stray page numbers
        self.assertTrue(paras[-1]["text"].startswith("綜上，"))

    def test_hearings_match_official_videos(self):
        media = json.loads((ROOT / "data/election-media.json").read_text())["national_videos"]
        h = self.r["hearings"]
        self.assertEqual([x["no"] for x in h], [1, 2, 3, 4, 5])
        self.assertEqual([x["video"] for x in h], [v["video"] for v in media])
        for x in h:
            self.assertRegex(x["video"], r"^[A-Za-z0-9_-]{11}$")
            self.assertTrue(x["pro"] and x["con"] and x["host"])

    def test_sources_are_official(self):
        for s in self.r["sources"]:
            self.assertRegex(s["url"], r"^https://(web\.cec\.gov\.tw|bulletin\.cec\.gov\.tw|law\.moj\.gov\.tw)/")


if __name__ == "__main__":
    unittest.main()
