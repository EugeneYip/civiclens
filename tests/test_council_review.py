import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class CouncilReviewTests(unittest.TestCase):
 def test_scope(self):
  d=json.loads((R/'data/taipei-council-review.json').read_text());self.assertEqual(d['release_status'],'blocked_pending_independent_review');self.assertEqual(len(d['districts']),8)
  rows=[r for x in d['districts'] for r in x['candidates']]
  self.assertEqual(len(rows),97);self.assertEqual(len({r['id'] for r in rows}),97);self.assertEqual(sum(x['seats'] for x in d['districts']),61)
  for x in d['districts']:
   self.assertEqual([r['ballot_number'] for r in x['candidates']],list(range(1,len(x['candidates'])+1)))
   for r in x['candidates']:
    self.assertIs(r['publication_allowed'],False);self.assertIsNone(r['recommending_party']);self.assertEqual(r['evidence']['name']['notice']['page'],2)
 def test_preview(self):
  for p in ['preview/compare.js','preview/candidate.js']:
   self.assertIn('taipei-council-review.json',(R/p).read_text())
