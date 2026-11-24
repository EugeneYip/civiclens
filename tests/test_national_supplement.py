import json, unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class NationalSupplement(unittest.TestCase):
 def test_scope(self):
  old=json.loads((R/'data/published-roster.json').read_text()); n=json.loads((R/'data/national-roster-supplement.json').read_text()); groups=old['districts']+n['districts']; rows=[r for d in groups for r in d['candidates']]
  self.assertEqual(len(groups),243); self.assertEqual(len({d['id'] for d in groups}),243); self.assertEqual(len(rows),1574); self.assertEqual(len({r['id'] for r in rows}),1574)
  self.assertEqual(sum(len(d['candidates']) for d in groups if d['office']=='chief'),81); self.assertEqual(sum(len(d['candidates']) for d in groups if d['office']=='council'),1493)
  for d in n['districts']:
   self.assertTrue(d['review'].startswith('secondary')); self.assertEqual([r['number'] for r in d['candidates']],list(range(1,len(d['candidates'])+1)))
 def test_video(self):
  d=json.loads((R/'data/election-media.json').read_text()); self.assertEqual(sum(bool(x.get('video')) for x in d['entries']),3)
  self.assertTrue(all('cec.gov.tw' in x['source'] for x in d['entries']))
  self.assertIn('youtube-nocookie.com/embed/',(R/'scripts/explorer.js').read_text())
 def test_no_fake_performance(self):
  d=json.loads((R/'data/policy-tracking.json').read_text()); self.assertEqual(d['records'],[])
