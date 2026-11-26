import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = {"交通", "居住與都市", "教育與青年", "育兒與社福", "醫療與健康", "經濟與就業", "環境與能源", "文化與觀光", "治理與安全"}


class ChiefBulletinPolicyTests(unittest.TestCase):
    def test_structure(self):
        d = json.loads((ROOT / "data/chief-bulletin-policies.json").read_text())
        self.assertEqual(d["version"], "0.1.50")
        pilot = json.loads((ROOT / "data/reviewed-policy-pilot.json").read_text())["records"]
        self.assertEqual(set(d["records"]), set(pilot))  # every mayor/magistrate candidate
        for k, r in d["records"].items():
            self.assertEqual((r["name"], r["number"]), (pilot[k]["name"], pilot[k]["number"]), k)
            self.assertTrue(r["source"].startswith(pilot[k]["source"].split("#")[0] + "#page="), k)
            self.assertTrue(any(s["kind"] in ("policy", "intro") for s in r["sections"]), k)
            for s in r["sections"]:
                self.assertIn(s["kind"], ("policy", "record", "intro"))
                self.assertTrue(s["items"])
                for it in s["items"]:
                    self.assertTrue(it["text"] and it["text"] == it["text"].strip())
                    self.assertNotRegex(it["text"], "[０-９]")
                    self.assertTrue(1 <= len(it["topics"]) <= 2 and set(it["topics"]) <= TOPICS, it)


if __name__ == "__main__":
    unittest.main()
