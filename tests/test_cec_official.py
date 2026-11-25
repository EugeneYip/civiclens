import json, re, unittest
from pathlib import Path
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "data" / (name + ".json")).read_text())


class CecOfficialTests(unittest.TestCase):
    def setUp(self):
        self.d = load("cec-official-2026")
        self.rows = {c["id"]: c for f in ("published-roster", "national-roster-supplement") for g in load(f)["districts"] for c in g["candidates"]}

    def test_complete_official_coverage(self):
        self.assertEqual(self.d["version"], "0.1.26")
        self.assertEqual(set(self.d["records"]), set(self.rows))
        audit = load("photo-identity-audit")
        self.assertEqual(self.d["problems"], [{"source": "photo_audit", "id": k, "reason": "displayed_image_is_not_registration_photo"} for k in sorted(audit["rejected"])])
        self.assertEqual(self.d["party_conflicts"], [])
        for f in self.d["sources"]["cec"]["files"]:
            u = urlparse(f["url"])
            self.assertEqual((u.scheme, u.hostname), ("https", "info.cec.gov.tw"))
            self.assertRegex(f["sha256"], "^[0-9a-f]{64}$")

    def test_photo_identity_audit(self):
        audit = load("photo-identity-audit")
        self.assertEqual(audit["stats"]["checked"], len(self.d["records"]))
        self.assertEqual(audit["stats"]["unreadable"], 0)
        self.assertGreaterEqual(audit["stats"]["min_accepted"], audit["threshold"])
        for k, x in audit["rejected"].items():
            self.assertLess(x["similarity"], audit["threshold"])
            self.assertNotIn("photo", self.d["records"][k], k)  # a rejected image is never displayed
        self.assertIn("02-council-4-12", audit["rejected"])  # gazette showed a party emblem for this candidate
        self.assertEqual(sum("photo" in x for x in self.d["records"].values()), len(self.d["records"]) - len(audit["rejected"]))

    def test_fields(self):
        for k, x in self.d["records"].items():
            r = self.rows[k]
            self.assertIn(x["gender"], ("男", "女"), k)
            self.assertTrue(1920 <= x["birth_year"] <= 2006, k)  # at least 20 years old on 2026-11-28
            if "photo" in x:
                self.assertRegex(x["photo"], "^[0-9a-f]{64}$")
            self.assertTrue(x["cec_photo"].startswith("/json/portrait/cand/"))
            self.assertRegex(x["page"], r"^https://gazette2026\.taiwangogo\.tw/candidates/[0-9a-f-]{36}/$")
            self.assertTrue(x["party"])
            if r.get("party") is not None:
                self.assertEqual(r["party"], x["party"], k)
            if x.get("official_name"):
                self.assertTrue(re.sub(r"\s", "", x["official_name"]).startswith(re.sub(r"\s", "", r["name"])), k)
        for party, path in self.d["emblems"].items():
            self.assertNotEqual(party, "無")
            self.assertRegex(path, r"^/brand/party-emblems/[A-Za-z0-9._-]+\.webp$")

    def test_verified_corrections(self):
        expect = {"01-council-1-7": "劉致妤", "01-council-5-1": "張延廷", "01-council-5-14": "應佳妤", "01-council-8-1": "孔垂崢 Haisul Islituan"}
        for k, name in expect.items():
            self.assertEqual(self.rows[k]["name"], name)
            self.assertNotIn("source_conflict", self.rows[k])
            self.assertIn("previous", self.rows[k]["name_verification"])
        self.assertEqual(self.rows["05-chief-1"]["party"], "司法改革黨")
        self.assertFalse(any(r.get("source_conflict") for r in self.rows.values()))


class BulletinQuarantineTests(unittest.TestCase):
    def test_quarantine_is_evidence_based(self):
        q = load("bulletin-quarantine")
        facts = load("bulletin-facts")["records"]
        official = load("cec-official-2026")["records"]
        groups = {g["id"]: g for f in ("published-roster", "national-roster-supplement") for g in load(f)["districts"]}
        self.assertEqual(q["version"], "0.1.26")
        races = {e["race"] for e in q["evidence"]}
        self.assertIn("04-council-8", races)
        expected = {c["id"] for r in races for c in groups[r]["candidates"] if c["id"] in facts}
        self.assertEqual(set(q["ids"]), expected)
        for e in q["evidence"]:
            for m in e["mismatches"]:
                self.assertNotEqual(m["transcribed_party"], m["official_party"])
                cid = groups[e["race"]]["id"] + "-" + str(m["number"])
                self.assertEqual(official[cid]["party"], m["official_party"])
        for shard in (ROOT / "data/county").glob("*.json"):
            x = json.loads(shard.read_text())
            self.assertFalse(set(x["bulletin"]["records"]) & set(q["ids"]), shard.name)


if __name__ == "__main__":
    unittest.main()
