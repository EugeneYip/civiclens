import json, unittest, re, subprocess, sys
from pathlib import Path
from urllib.parse import urlparse,parse_qs
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/election.json').read_text())
class DataTests(unittest.TestCase):
 def test_counties(self):
  self.assertEqual(len(d['counties']),22)
  self.assertEqual(len({x['name'] for x in d['counties']}),22)
  self.assertEqual([x['code'] for x in d['counties']],[f'{i:02}' for i in range(1,23)])
  for x in d['counties']:
   u=urlparse(x['url']);self.assertEqual(u.scheme,'https');self.assertEqual(u.hostname,'eebulletin.cec.gov.tw');self.assertEqual(parse_qs(u.query)['dir'],['115/'+x['code']+x['name']])
 def test_counts(self):
  self.assertEqual(len(d['offices']),9)
  self.assertEqual([sum(x[k] for x in d['offices']) for k in ('seats','registered','candidates')],[11051,19695,19100])
  self.assertTrue(all(0<x['seats']<=x['candidates']<=x['registered'] for x in d['offices']))
 def test_sources(self):
  ids={s['id'] for s in d['sources']}
  for x in d['counties']+d['offices']:self.assertIn(x['source_id'],ids)
 def test_no_unverified_candidates(self):
  self.assertEqual(d['candidate_records'],[]);self.assertEqual(d['candidate_status'],'not_imported')
 def test_build_reproducibility(self):
  before=(root/'index.html').read_bytes();subprocess.run([sys.executable,str(root/'scripts/build.py')],check=True);self.assertEqual(before,(root/'index.html').read_bytes())
 def test_static_page(self):
  s=(root/'index.html').read_text();self.assertEqual(s.count('class="county"'),22);self.assertEqual(s.count('<tr><th scope="row">'),10);self.assertNotIn('<!--COUNTIES-->',s);self.assertIn('lang="zh-Hant-TW"',s)
if __name__=='__main__':unittest.main()
