import datetime as dt,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from stage_results import build,merge,maps,OPEN,validate_snapshot
class StageResultsTests(unittest.TestCase):
 def setUp(self):
  self.g={"01-chief":{"candidates":[{"id":"01-chief-1","name":"甲","number":1},{"id":"01-chief-2","name":"乙","number":2}]}}
  self.s={"01-chief":1};self.t=(OPEN+dt.timedelta(minutes=1)).isoformat()
  self.now=OPEN+dt.timedelta(hours=1)
  self.rows=[dict(county="01",office="chief",district="",number="1",name="甲",votes="6",elected="true",valid_votes="10"),dict(county="01",office="chief",district="",number="2",name="乙",votes="4",elected="false",valid_votes="10")]
 def run_build(self,rows=None,status="final",now=None,source="https://vote.cec.gov.tw/zh-TW/result.html"):
  return build(self.rows if rows is None else rows,self.g,self.s,source,self.t,status,"a"*64,now or self.now)
 def test_snapshot(self):
  g,s=maps();self.assertTrue(validate_snapshot({"version":"0.1.22","election_date":"2026-11-28","status":"not_published","races":{}},g,s,self.now))
  with self.assertRaises(ValueError):validate_snapshot({"version":"0.1.22","election_date":"2026-11-28","status":"published_data_available","races":{}},g,s,self.now)
 def test_scope(self):
  g,s=maps();self.assertEqual(len(g),243);self.assertEqual(sum(s.values()),941)
 def test_final(self):
  a=self.run_build();self.assertEqual(a["01-chief"]["valid_votes"],10)
  self.assertEqual(merge(a,a),a)
  for rows in (self.rows[:1],self.rows+[self.rows[0]],[{**self.rows[0],"name":"乙"},self.rows[1]],[{**self.rows[0],"votes":"-1"},self.rows[1]],[{**self.rows[0],"elected":"false"},self.rows[1]]):
   with self.assertRaises(ValueError):self.run_build(rows)
 def test_release_source(self):
  with self.assertRaises(ValueError):self.run_build(now=OPEN-dt.timedelta(seconds=1))
  with self.assertRaises(ValueError):self.run_build(source="https://vote.cec.gov.tw.evil.test/x")
 def test_partial_and_no_downgrade(self):
  p=self.run_build([{**self.rows[0],"elected":""}],"preliminary")
  f=self.run_build();self.assertEqual(merge({},f),f)
  with self.assertRaises(ValueError):merge(f,p)
  with self.assertRaises(ValueError):merge(p,f) # same timestamp conflicting
