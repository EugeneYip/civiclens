import json, re, shutil, subprocess, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CountdownTests(unittest.TestCase):
 def test_markup(self):
  page=(ROOT/'index.html').read_text()
  self.assertIn('11.28 <span>星期六</span>',page)
  self.assertIn('2026 · 115 年地方公職人員選舉',page)
  self.assertIn('距離投票日期還有',page)
  self.assertEqual(len(re.findall(r'id="countdown-clock"',page)),1)
 @unittest.skipUnless(shutil.which('node'),'Node.js required for JavaScript boundary test')
 def test_time_boundaries(self):
  js=(ROOT/'scripts/app.js').read_text().split('const byId=')[0]
  cases=[['2026-11-27T23:59:59+08:00','date',0,0,0,1],['2026-11-28T00:00:00+08:00','opening',0,8,0,0],['2026-11-28T08:00:00+08:00','closing',0,8,0,0],['2026-11-28T15:59:59+08:00','closing',0,0,0,1],['2026-11-28T16:00:00+08:00','ended',0,0,0,0],['2026-11-27T11:00:00-05:00','opening',0,8,0,0],['2026-11-29T00:00:00+08:00','ended',0,0,0,0]]
  js+='\nconst cases='+json.dumps(cases)+'; for(const [date,...want] of cases){const r=countdownState(Date.parse(date)); const got=[r.phase,r.days,r.hours,r.minutes,r.seconds];if(JSON.stringify(got)!==JSON.stringify(want))throw Error(date+JSON.stringify(got));}'
  subprocess.run(['node','-e',js],check=True)
