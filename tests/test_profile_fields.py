import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class ProfileFields(unittest.TestCase):
 def test_sources_and_coverage(self):
  d=json.loads((R/'data/chief-roster-review.json').read_text()); rows=[r for x in d['districts'] for r in x['candidates']]
  self.assertEqual(len(rows),81);self.assertEqual(sum(r.get('registration_recommending_party') is not None for r in rows),20)
  self.assertEqual(sum(r['education'] is not None for r in rows),8);self.assertEqual(sum(r['experience'] is not None for r in rows),8);self.assertEqual(sum(r['platform'] is not None for r in rows),7)
  for r in rows:
   self.assertIs(r['publication_allowed'],False)
   if r.get('registration_recommending_party') is not None:
    self.assertIsNone(r['recommending_party']);self.assertEqual(r['evidence']['registration_recommending_party']['kind'],'registration_snapshot')
   for k in ('education','experience','platform'):
    if r[k] is not None:self.assertEqual(r['evidence'][k]['kind'],'candidate_self_report')
