"""Fetch the CEC count page for national referendum No. 22 and write data/referendum-result.json.

Source: https://vote.cec.gov.tw/2026-ref/zh-TW/F1/00000000000000000.html (national totals,
updated by the CEC every minute). Nothing is estimated. The script refuses to write unless:
agree + disagree = valid; valid + invalid = ballots cast; stations reported <= total; the
electorate equals the figure in data/referendum.json; and the update time is after polls closed.
The outcome under Referendum Act Art. 29 is stated only when every station has reported.

Usage: python3 -I scripts/build_referendum_result.py RAW_DIR [--out PATH]
"""
import html
import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

URL = "https://vote.cec.gov.tw/2026-ref/zh-TW/F1/00000000000000000.html"
ROOT = Path(__file__).resolve().parents[1]
OPENING = datetime.fromisoformat("2026-11-28T16:00:00+08:00")
FIELDS = {"同意票數": "agree", "不同意票數": "disagree", "有效票數": "valid", "無效票數": "invalid", "投票數": "ballots",
          "已完成投票所投票權人數": "electorate_reported", "投票權人總數": "electorate"}


def parse(text):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.S)
    st = re.search(r"已送投票所數/總投票所數:\s*([\d,]+)\s*/\s*([\d,]+)", t)
    upd = re.search(r"資料更新時間:(?:&nbsp;|\s)*(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})", t)
    if not st or not upd or "第22案" not in t:
        raise ValueError("unexpected page layout")
    heads = [re.sub(r"\s+", "", html.unescape(h)) for h in re.findall(r"<th\b[^>]*>(.*?)</th>", t, re.S)]
    vals = [re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", v))) for v in re.findall(r"<td\b[^>]*>(.*?)</td>", t, re.S)]
    if len(heads) != len(vals):
        raise ValueError("header/value count mismatch %d/%d" % (len(heads), len(vals)))
    row = dict(zip(heads, vals))
    out = {}
    for h, k in FIELDS.items():
        if h not in row or not re.fullmatch(r"[\d,]+", row[h]):
            raise ValueError("missing or non-integer field " + h)
        out[k] = int(row[h].replace(",", ""))
    mo, dd, hh, mi = map(int, upd.groups())
    out.update(reported=int(st.group(1).replace(",", "")), stations=int(st.group(2).replace(",", "")),
               published_at="2026-%02d-%02dT%02d:%02d:00+08:00" % (mo, dd, hh, mi))
    return out


def validate(r, electorate):
    if r["agree"] + r["disagree"] != r["valid"]:
        raise ValueError("agree + disagree != valid")
    if r["valid"] + r["invalid"] != r["ballots"]:
        raise ValueError("valid + invalid != ballots")
    if not 0 <= r["reported"] <= r["stations"] or r["stations"] == 0:
        raise ValueError("station counts")
    if r["electorate"] != electorate:
        raise ValueError("electorate differs from the CEC announcement in data/referendum.json")
    if r["ballots"] > r["electorate_reported"] or r["electorate_reported"] > r["electorate"]:
        raise ValueError("ballots exceed electorate")
    if datetime.fromisoformat(r["published_at"]) < OPENING:
        raise ValueError("update time before polls closed")


def main(argv):
    raw = Path(argv[0]); raw.mkdir(parents=True, exist_ok=True)
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "data/referendum-result.json"
    dest = raw / "ref_F1.html"
    if subprocess.run(["curl", "-s", "-f", "-m", "40", "--retry", "2", "-o", str(dest), URL]).returncode:
        raise SystemExit("fetch failed")
    ref = json.loads((ROOT / "data/referendum.json").read_text())
    r = parse(dest.read_text(encoding="utf-8", errors="replace"))
    validate(r, ref["electorate"]["count"])
    need = ref["threshold"]["votes_needed"]
    if need != math.ceil(r["electorate"] / 4):
        raise ValueError("threshold mismatch")
    final = r["reported"] == r["stations"]
    doc = {"version": "0.1.79", "case": ref["case"], "source": URL, "published_at": r["published_at"],
           "status": "complete" if final else "counting", "stations": {"reported": r["reported"], "total": r["stations"]},
           "agree": r["agree"], "disagree": r["disagree"], "valid": r["valid"], "invalid": r["invalid"], "ballots": r["ballots"],
           "electorate_reported": r["electorate_reported"], "electorate": r["electorate"], "votes_needed": need}
    if final:  # Referendum Act Art. 29: agree > disagree and agree >= one quarter of the electorate
        doc["meets_threshold"] = r["agree"] > r["disagree"] and r["agree"] >= need
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: doc[k] for k in ("published_at", "status", "stations", "agree", "disagree")}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
