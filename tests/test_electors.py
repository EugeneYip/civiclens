import json, unittest, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'data/electors.json').read_text())
E=json.loads((ROOT/'data/election.json').read_text())
class ElectorTests(unittest.TestCase):
 def test_scope_and_totals(self):
  self.assertEqual(set(D['counties']),{x['name'] for x in E['counties']})
  self.assertEqual(len(D['counties']),22)
  self.assertEqual(D['totals'],[19576028,19486232,5043956,5038121,19439382,20003835])
  self.assertTrue(all(len(x)==6 and all(type(v) is int and v>=0 for v in x) for x in D['counties'].values()))
  self.assertEqual([sum(r[i] for r in D['counties'].values()) for i in range(6)],D['totals'])
 def test_source_and_render(self):
  self.assertEqual(D['published_on'],'2026-11-24')
  self.assertEqual(D['source_url'],'https://web.cec.gov.tw/central/article/66267')
  self.assertTrue(D['local_pdf'].endswith('8998d12c-82f2-4711-92db-1b49c895be2a.pdf'))
  self.assertTrue(D['referendum_pdf'].endswith('bc81d816-ce36-4140-b1a3-3f88cf6d7adc.pdf'))
  page=(ROOT/'index.html').read_text()
  self.assertEqual(json.loads(re.search(r'id="elector-data">(.*?)</script>',page,re.S).group(1)),D)
  self.assertIn('非實際行政界線',page)
  self.assertIn('全國性公投 · 第22案',page)
 def test_known_rows(self):
  self.assertEqual(D['counties']['臺北市'],[2031431,2026809,0,0,2015296,2072492])
  self.assertEqual(D['counties']['連江縣'],[11679,11667,11662,11662,11633,12078])
