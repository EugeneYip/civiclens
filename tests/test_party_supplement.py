import json, unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]/'data'
class PartySupplementTests(unittest.TestCase):
 def test_identity_and_precedence(self):
  rows={r['id']:r for f in ('published-roster','national-roster-supplement') for d in json.loads((R/(f+'.json')).read_text())['districts'] for r in d['candidates']}
  data=json.loads((R/'candidate-parties.json').read_text())
  records=data['records']
  self.assertEqual(len(records),data['stats']['added'])
  self.assertEqual(len(records)+len(data['unmatched']),data['stats']['missingBefore'])
  self.assertEqual(sum(r['party'] is not None for r in rows.values()),971)
  for k,x in records.items():
   r=rows[k]
   self.assertEqual(x['name'],r['name'])
   self.assertIsNone(r['party'])
   self.assertIsNone(r.get('registration_party'))
   self.assertFalse(r.get('source_conflict'))
   self.assertTrue(x['party'])
   self.assertEqual(x['status'],'registration_secondary_exact_match')
   self.assertTrue(x['source'].startswith('https://github.com/weryk153/legislator-background/blob/6d648312aed33a745b99fbfc37c95266125b8e51/'))
   self.assertEqual(x['registrationSource'],'https://web.cec.gov.tw/central/article/64709')
  self.assertEqual(data['stats']['displayable'],977+len(records))
