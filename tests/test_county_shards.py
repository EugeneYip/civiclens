import json, subprocess, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


class CountyShardTests(unittest.TestCase):
    def test_shards_current_and_complete(self):
        subprocess.run([sys.executable, str(ROOT / "scripts/build_county_shards.py"), "--check"], check=True)
        official = json.loads((ROOT / "data/cec-official-2026.json").read_text())["records"]
        careers = json.loads((ROOT / "data/candidate-careers.json").read_text())["records"]
        seen = {}
        for f in sorted((ROOT / "data/county").glob("*.json")):
            x = json.loads(f.read_text())
            self.assertEqual(x["version"], "0.1.44")
            self.assertEqual(x["county"], f.stem)
            for k, v in x["official"]["records"].items():
                self.assertTrue(k.startswith(f.stem + "-"))
                self.assertEqual(v, official[k])
                seen[k] = 1
            for k, v in x["careers"]["records"].items():
                self.assertEqual(v, careers[k])
        self.assertEqual(set(seen), set(official))
        js = (ROOT / "scripts/explorer.js").read_text()
        self.assertIn('"data/county/"', js)
        self.assertNotIn("data/candidate-careers.json", js)


if __name__ == "__main__":
    unittest.main()
