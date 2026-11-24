import json, unittest
from pathlib import Path
class ChiefReview(unittest.TestCase):
 def test_invariants(self):
  d=json.loads((Path(__file__).resolve().parents[1]/"data/chief-roster-review.json").read_text())
  self.assertEqual(d["release_status"],"blocked_pending_independent_review")
  self.assertEqual(len(d["districts"]),22)
  self.assertEqual(len({x["district_id"] for x in d["districts"]}),22)
  rows=[r for x in d["districts"] for r in x["candidates"]]
  self.assertEqual(len(rows),81)
  self.assertEqual(len({r["id"] for r in rows}),81)
  self.assertEqual(sum(bool(x["candidates"]) for x in d["districts"]),22)
  self.assertEqual(sum(r["recommending_party"] is not None for r in rows),60)
  for x in d["districts"]:
   self.assertEqual([r["ballot_number"] for r in x["candidates"]],list(range(1,len(x["candidates"])+1)))
   for r in x["candidates"]:
    self.assertIs(r["publication_allowed"],False)
    self.assertTrue((r["evidence"]["name"].get("notice") or r["evidence"]["name"].get("identity_source"))["url"].startswith(("https://web.cec.gov.tw/","https://www.cec.gov.tw/")))
    self.assertEqual(r["evidence"]["recommending_party"] is None,r["recommending_party"] is None)
    self.assertTrue(all(r[k] is None for k in ("education","experience","platform")))
if __name__=="__main__": unittest.main()
