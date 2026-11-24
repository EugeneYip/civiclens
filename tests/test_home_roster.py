import json, unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class HomeRoster(unittest.TestCase):
 def test_roster(self):
  d=json.loads((R/'data/published-roster.json').read_text())
  rows=[r for x in d['districts'] for r in x['candidates']]
  self.assertEqual(len(rows),103);self.assertEqual(len({r['id'] for r in rows}),103)
  self.assertEqual([len(x['candidates']) for x in d['districts']],[6,20,13,13,14,14,18,2,3])
  for x in d['districts']:
   self.assertEqual([r['number'] for r in x['candidates']],list(range(1,len(x['candidates'])+1)))
   for r in x['candidates']:
    self.assertIn('cec.gov.tw',r['name_source']['url']);self.assertIn('cec.gov.tw',r['party_source']['url']);self.assertIsNone(r['performance'])
 def test_home(self):
  s=(R/'index.html').read_text();self.assertLess(s.index('class="county-grid"'),s.index('id="county-panel"'))
  self.assertIn('id="explorer"',s);self.assertIn('scripts/explorer.js?v=019',s)
  self.assertNotIn('id="county-search"',s)
