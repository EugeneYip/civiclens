import json, unittest, re
from pathlib import Path
from urllib.parse import urlparse,parse_qs,unquote
R=Path(__file__).resolve().parents[1]
class GazetteTests(unittest.TestCase):
 def test_catalog(self):
  g=json.loads((R/'data/gazettes.json').read_text()); e=json.loads((R/'data/election.json').read_text())
  self.assertEqual([(c['code'],c['name']) for c in g['counties']],[(c['code'],c['name']) for c in e['counties']])
  docs=[]
  for c in g['counties']:
   self.assertEqual(len({o['id'] for o in c['offices']}),len(c['offices']))
   for o in c['offices']:
    u=urlparse(o['directory']);self.assertEqual((u.scheme,u.netloc),('https','eebulletin.cec.gov.tw'))
    self.assertTrue(parse_qs(u.query)['dir'][0].startswith('115/'+c['code']+c['name']+'/'))
    for d in o['documents']:
     p=urlparse(d['url']);self.assertEqual((p.scheme,p.netloc),('https','eebulletin.cec.gov.tw'));self.assertTrue(unquote(p.path).startswith('/'+parse_qs(u.query)['dir'][0]+'/')); self.assertIn(d['status'],['retrieved_pdf','fetch_limit','not_found']);docs.append(d)
  self.assertEqual(len(docs),31);self.assertEqual(len({d['id'] for d in docs}),31)
  self.assertEqual(sum(d['status']=='retrieved_pdf' for d in docs),25)
  self.assertEqual(sum(d['status']=='fetch_limit' for d in docs),5)
  self.assertEqual(sum(d['status']=='not_found' for d in docs),1)
 def test_title_and_links(self):
  p=(R/'index.html').read_text();self.assertIn('<title>11.28｜115年地方公職人員選舉</title>',p);self.assertIn('href="gazettes.html"',p);self.assertIn('id="official-directory"',p)
  self.assertIn('id="pdf"',(R/'gazettes.html').read_text())

 def test_taitung_fallback(self):
  g=json.loads((R/'data/gazettes.json').read_text())
  d=next(o for c in g['counties'] if c['code']=='14' for o in c['offices'] if o['id']=='chief')['documents'][0]
  self.assertEqual(d['status'],'not_found');self.assertEqual(d['fallback']['status'],'fetch_limit')
  p=urlparse(d['fallback']['url']);self.assertEqual((p.scheme,p.netloc),('https','bulletin.cec.gov.tw'))
  self.assertEqual(unquote(p.path),'/01選舉公報/04縣市長/115年/臺東縣縣長.pdf')
 def test_results_no_vote_claim(self):
  p=(R/'results.html').read_text();self.assertIn('尚未串接即時票數',p);self.assertIn('https://www.cec.gov.tw/',p)
  self.assertIn('2026-11-28T16:00:00+08:00',(R/'scripts/results.js').read_text())
  self.assertIn('href="results.html"',(R/'index.html').read_text())
