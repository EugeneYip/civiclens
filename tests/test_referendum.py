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

    def test_voting_notes_follow_gazette(self):
        self.assertIn("投票當日，戶政事務所不受理換補發國民身分證", self.r["bring"])
        notes = self.r["notes"]
        self.assertEqual(len(notes), 4)
        self.assertIn("公民投票法第43條", notes[2]["text"])
        self.assertEqual(len(notes[2]["items"]), 3)
        self.assertTrue(notes[3].endswith("依公民投票法第41條規定，處1年以下有期徒刑、拘役或科新臺幣1萬5千元以下罰金。"))
        self.assertEqual([p["law"] for p in self.r["penalties"]], ["公民投票法第42條", "公民投票法第44條", "刑法第143條"])
        self.assertEqual(len(self.r["invalid"]), 9)

    def test_sources_are_official(self):
        for s in self.r["sources"]:
            self.assertRegex(s["url"], r"^https://(web\.cec\.gov\.tw|bulletin\.cec\.gov\.tw|law\.moj\.gov\.tw)/")


if __name__ == "__main__":
    unittest.main()
