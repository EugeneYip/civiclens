import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class SecondarySourceTests(unittest.TestCase):
 def test_audit(self):
  a=json.loads((R/'data/secondary-roster-audit.json').read_text());r=json.loads((R/'data/published-roster.json').read_text())
  self.assertEqual(sum(len(x['rows']) for x in a['snapshots']),103)
  self.assertEqual(len(a['conflicts']),4)
  self.assertEqual(sum('supplemental_education' in x for y in r['districts'] for x in y['candidates']),11)
  self.assertTrue(all(x['education'] is None for y in r['districts'] for x in y['candidates'] if 'supplemental_education' in x))
 def test_media(self):
  d=json.loads((R/'data/media-assets.json').read_text());self.assertTrue({'01-chief-5','01-chief-3'} <= set(d['photos']));self.assertEqual(len(d['parties']),3)
  for x in list(d['photos'].values())+list(d['parties'].values()):
   self.assertEqual(x['status'],'source_license_documented');self.assertTrue(x['source'].startswith('https://commons.wikimedia.org/'));self.assertNotIn('taiwangogo.tw',x['src'])
