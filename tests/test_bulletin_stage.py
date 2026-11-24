import importlib.util
import sqlite3
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("stage_bulletin",Path(__file__).resolve().parents[1]/"scripts/stage_bulletin.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class BulletinStageTests(unittest.TestCase):
 def test_source_and_identity(self):
  db=sqlite3.connect(":memory:")
  db.executescript("""CREATE TABLE candidates(candidate_id INTEGER,name TEXT,district TEXT,election_id INTEGER);
  CREATE TABLE candidate_bulletin_profiles(candidate_id INTEGER,election_id INTEGER,ballot_no INTEGER,source_url TEXT,source_page INTEGER,source_kind TEXT,party_raw TEXT,education TEXT,career TEXT);
  CREATE TABLE platforms(candidate_id INTEGER,election_id INTEGER,seq INTEGER,content TEXT,content_raw TEXT,source_url TEXT,note TEXT);""")
  url="https://eebulletin.cec.gov.tw/115/example.pdf"
  for i,name in enumerate(["甲","乙","丙"],1):
   db.execute("INSERT INTO candidates VALUES (?,?,?,?)",(i,name,"臺北市",77))
   db.execute("INSERT INTO candidate_bulletin_profiles VALUES (?,?,?,?,?,?,?,?,?)",(i,77,i,url if i!=3 else "https://example.org/file.pdf",1,"text_layer","無",'["學歷"]','["經歷"]'))
   db.execute("INSERT INTO platforms VALUES (?,?,?,?,?,?,?)",(i,77,1,"政見","政見",url,"公報原文照抄"))
   db.execute("INSERT INTO platforms VALUES (?,?,?,?,?,?,?)",(i,77,2,"不一致","原文",url,"公報原文照抄"))
  idx={("chief","臺北市",i,n):[{"id":str(i),"name":n,"number":i,**({"source_conflict":True} if i==2 else {})}] for i,n in enumerate(["甲","乙","丙"],1)}
  x=m.stage(db,idx)
  self.assertEqual(x["stats"]["matched"],1)
  self.assertEqual(x["stats"]["excluded"],2)
  self.assertEqual(x["records"]["1"]["policy"],["政見"])
  self.assertEqual(x["records"]["1"]["status"],"review_required")
 def test_unsafe_url(self):
  self.assertFalse(m.official_url("https://web.cec.gov.tw.example.org/x.pdf"))
  self.assertFalse(m.official_url("http://web.cec.gov.tw/x.pdf"))
  self.assertFalse(m.official_url("https://web.cec.gov.tw/x.html"))
