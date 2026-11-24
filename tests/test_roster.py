import copy, json, unittest, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_roster import validate

class RosterTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "data/roster-pilot.json").read_text())
    def test_complete_pilot(self):
        self.assertEqual(validate(self.data), 6)
    def test_missing_record(self):
        self.data["records"].pop()
        with self.assertRaises(ValueError): validate(self.data)
    def test_duplicate_number(self):
        self.data["records"][1]["ballot_number"] = 1
        with self.assertRaises(ValueError): validate(self.data)
    def test_evidence_required(self):
        self.data["records"][0]["fields"]["name"]["evidence"] = []
        with self.assertRaises(ValueError): validate(self.data)
    def test_publication_block(self):
        self.data["release_status"] = "approved"
        with self.assertRaises(ValueError): validate(self.data)
    def test_scope_isolation(self):
        self.data["records"][0]["jurisdiction_code"] = "02"
        with self.assertRaises(ValueError): validate(self.data)
    def test_unverified_field(self):
        self.data["records"][0]["fields"]["name"]["status"] = "pending"
        with self.assertRaises(ValueError): validate(self.data)
