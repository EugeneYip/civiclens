import unittest,json,re,struct
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class IdentityTests(unittest.TestCase):
 def test_metadata(self):
  p=(R/'index.html').read_text()
  self.assertIn('<title>11.28｜115年地方公職人員選舉</title>',p)
  for path in ['/favicon.ico','/assets/favicon.svg','/apple-touch-icon.png']: self.assertIn('href="'+path+'"',p)
  self.assertIn('property="og:url" content="https://civiclens.eugeneyip.net/"',p)
 def test_icons(self):
  b=(R/'apple-touch-icon.png').read_bytes();self.assertEqual(b[:8],b'\x89PNG\r\n\x1a\n');self.assertEqual(struct.unpack('>II',b[16:24]),(180,180))
  i=(R/'favicon.ico').read_bytes();self.assertEqual(i[:6],b'\x00\x00\x01\x00\x01\x00');self.assertEqual(i[6:8],bytes([32,32]))
  self.assertIn('viewBox="0 0 64 64"',(R/'assets/favicon.svg').read_text())
 def test_source_scope(self):
  e=json.loads((R/'data/election.json').read_text());s=json.loads((R/'data/chief-sources.json').read_text());self.assertEqual(set(s),{c['name'] for c in e['counties']});self.assertTrue(all(u.startswith('https://web.cec.gov.tw/') for u in s.values()));p=(R/'index.html').read_text();self.assertEqual(json.loads(re.search(r'id="chief-sources">(.*?)</script>',p,re.S).group(1)),s)
