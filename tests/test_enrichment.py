import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class EnrichmentTests(unittest.TestCase):
 def test_scope(self):
  ds=[d for p in ('published-roster','national-roster-supplement') for d in json.loads((R/'data'/f'{p}.json').read_text())['districts']];rows=[r for d in ds for r in d['candidates']]
  self.assertEqual(len(rows),1574);self.assertEqual(len({r['id'] for r in rows}),1574)
  self.assertEqual(sum(r['party'] is not None for r in rows),971);self.assertEqual(sum(r.get('registration_party') is not None and r['party'] is None for r in rows),6)
  self.assertTrue(all(r['performance'] is None for r in rows))
 def test_topics(self):
  ds=[d for p in ('published-roster','national-roster-supplement') for d in json.loads((R/'data'/f'{p}.json').read_text())['districts']];rows={r['id']:r for d in ds for r in d['candidates']};p=json.loads((R/'data/policy-topics.json').read_text())
  for r in p['records']:
   self.assertTrue(rows[r['id']]['platform']);self.assertTrue(r['source']);self.assertTrue(all(x in rows[r['id']]['platform'] for t in r['topics'] for x in t['excerpts']))
 def test_media(self):
  d=json.loads((R/'data/election-media.json').read_text());self.assertEqual(sum(bool(x.get("video")) for x in d["entries"]),25);self.assertTrue(all(x["verified"]["checked_on"]=="2026-11-25" for x in d["entries"] if x.get("video")));self.assertEqual(len(d["national_videos"]),5)
  self.assertEqual(len({x['video'] for x in d['entries'] if x.get('video')}),25)
  self.assertEqual(len({x['county'] for x in d['entries'] if x.get('video')}),15)
  self.assertEqual(sorted(n for x in d['entries'] if x['county']=='01' and x['office']=='council' for n in x['districts']),list(range(1,9)))
