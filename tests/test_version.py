import re, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


class VersionTests(unittest.TestCase):
    def test_single_version_source(self):
        v = (ROOT / "VERSION").read_text().strip()
        self.assertRegex(v, r"^\d+\.\d+\.\d+$")
        self.assertIn("## V" + v, (ROOT / "CHANGELOG.md").read_text())
        html = (ROOT / "index.html").read_text()
        self.assertIn('<a href="CHANGELOG.md">V' + v + "</a>", html)
        self.assertIn("explorer.js?v=" + v, html)
        self.assertNotIn("<!--VERSION-->", html)
        self.assertIn("**V" + v + " ", (ROOT / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
