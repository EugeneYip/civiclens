import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_policy_baseline import extract,tokens,valid_date,short_label,NUM,ACTIONS,OBJECTS,safe_url
class PolicyBaselineTests(unittest.TestCase):
 def test_dates_and_tokens(self):
  self.assertIsNone(valid_date(None));self.assertIsNone(valid_date("2026-11-25"))
  self.assertEqual(valid_date("2026-11-24T10:00:00"),"2026-11-24")
  self.assertEqual(tokens("增設社宅100戶"),(["增設"],["社宅"],["100戶"]))
  self.assertFalse(short_label("住址及學校"))
 def test_attribution(self):
  roster=[{"id":"01-chief-1","name":"甲","number":1}]
  c={"candidateId":"a","sourceId":"s","assertionType":"政策承諾","topic":"居住","subtopic":"社宅供給","quote":"增設社宅100戶"}
  d={"candidates":[{"id":"a","number":1,"name":"甲"}],"sources":[{"id":"s","candidateId":"a","url":"https://example.org/p","postedAt":"2026-11-01","text":"增設社宅100戶"}],"claims":[c,c,{**c,"quote":"不存在"}]}
  x,s=extract(d,roster)
  self.assertEqual(len(x),1);self.assertEqual(s["duplicate_quote"],1);self.assertEqual(s["quote_not_found"],1)
  self.assertEqual(next(iter(x.values()))["review_status"],"待原文人工核對")
 def test_generated(self):
  p=ROOT/"data/policy-review-baseline.json"
  if not p.exists():return
  d=json.loads(p.read_text())
  roster={r["id"]:r for f in ("published-roster","national-roster-supplement") for g in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] for r in g["candidates"]}
  self.assertEqual(d["stats"]["records"],len(d["records"]))
  self.assertEqual(d["stats"]["verified_promises"],0)
  self.assertEqual(d["stats"]["verified_performance"],0)
  self.assertEqual(d["stats"]["fulfillment_decisions"],0)
  for x in d["records"].values():
   self.assertEqual((x["name"],x["number"]),(roster[x["candidate_id"]]["name"],roster[x["candidate_id"]]["number"]))
   self.assertTrue(safe_url(x["source"]) and valid_date(x["date"]))
   self.assertTrue(set(x["actions"])<=set(ACTIONS) and set(x["objects"])<=set(OBJECTS))
   self.assertTrue(all(NUM.fullmatch(v) for v in x["numbers"]))
   self.assertEqual(x["review_status"],"待原文人工核對")
   self.assertNotIn("quote",x);self.assertNotIn("summary",x)
