"""Build data/results-snapshot.json from official CEC vote counts (2026-11-28 onward).

Input: one or more JSON files in the normalized form below, produced by an adapter from a
CEC source (live results site or db.cec.gov.tw).  Nothing is estimated: every row must match
the published roster exactly, and a race marked final must list every candidate, the elected
flags must equal the seat count and the votes must add up to the valid votes.

{
  "source": "https://<official CEC host>/...",       # page or file the counts came from
  "published_at": "2026-11-28T18:30:00+08:00",       # time stated by the CEC (with offset)
  "status": "preliminary" | "final",
  "races": [
    {"county": "臺北市", "office": "chief" | "council", "district": null | 1,
     "valid_votes": 1234567 | null,
     "candidates": [{"number": 1, "name": "…", "votes": 123, "elected": true | false | null}]}
  ]
}

Usage: python3 scripts/build_results_snapshot.py INPUT.json [INPUT2.json ...] [--out PATH] [--check]
The browser (scripts/results.js validateRace) repeats the same checks before showing anything.
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
VERSION = "0.1.22"  # read by scripts/results.js
OPENING = datetime.fromisoformat("2026-11-28T16:00:00+08:00")
OFFICIAL_HOSTS = {"www.cec.gov.tw", "web.cec.gov.tw", "info.cec.gov.tw", "db.cec.gov.tw", "vote.cec.gov.tw", "data.cec.gov.tw"}


class ResultError(ValueError):
    pass


def norm(name):
    return re.sub(r"[‧．·•・･.]", "‧", re.sub(r"\s+", "", name)).replace("台", "臺")


def load(name):
    return json.loads((DATA / name).read_text())


def roster():
    groups = [g for f in ("published-roster.json", "national-roster-supplement.json") for g in load(f)["districts"]]
    codes = {c["name"]: c["code"] for c in load("election.json")["counties"]}
    return {g["id"]: g for g in groups}, codes


def official(url):
    u = urlparse(url)
    return u.scheme == "https" and u.hostname in OFFICIAL_HOSTS and not u.username and not u.password and not u.port


def build_races(doc, groups, codes, now=None):
    if doc.get("status") not in ("preliminary", "final"):
        raise ResultError("status must be preliminary or final")
    if not official(doc.get("source") or ""):
        raise ResultError("source must be an official CEC https URL: %r" % doc.get("source"))
    stamp = datetime.fromisoformat(doc["published_at"])
    if stamp.tzinfo is None or stamp < OPENING:
        raise ResultError("published_at must carry an offset and be after polls close")
    if now is not None and stamp > now:
        raise ResultError("published_at is in the future")
    final = doc["status"] == "final"
    out = {}
    for race in doc["races"]:
        code = codes.get(race["county"].replace("台", "臺"))
        if not code:
            raise ResultError("unknown county %r" % race["county"])
        gid = f"{code}-{race['office']}" + (f"-{race['district']}" if race["office"] == "council" else "")
        g = groups.get(gid)
        if not g:
            raise ResultError("unknown race " + gid)
        if gid in out:
            raise ResultError("duplicate race " + gid)
        by_number = {c["number"]: c for c in g["candidates"]}
        rows, seen, total, winners = [], set(), 0, 0
        for v in race["candidates"]:
            c = by_number.get(v["number"])
            if not c or norm(v["name"]) != norm(c["name"]):
                raise ResultError(f"{gid}: number/name {v['number']} {v['name']} not in roster")
            if c["id"] in seen:
                raise ResultError(f"{gid}: duplicate candidate {c['id']}")
            if not isinstance(v["votes"], int) or isinstance(v["votes"], bool) or v["votes"] < 0:
                raise ResultError(f"{gid}: invalid votes for {c['id']}")
            row = {"id": c["id"], "name": c["name"], "number": c["number"], "votes": v["votes"]}
            if final:
                if not isinstance(v.get("elected"), bool):
                    raise ResultError(f"{gid}: final results need an elected flag for {c['id']}")
                row["elected"] = v["elected"]
                winners += v["elected"]
            elif v.get("elected") is not None:
                raise ResultError(f"{gid}: preliminary results must not mark winners")
            seen.add(c["id"]); total += v["votes"]; rows.append(row)
        valid = race.get("valid_votes")
        if valid is not None and (not isinstance(valid, int) or total > valid):
            raise ResultError(f"{gid}: candidate votes exceed valid votes")
        if final and (len(seen) != len(by_number) or winners != g["seats"] or valid != total):
            raise ResultError(f"{gid}: final race incomplete or inconsistent (candidates {len(seen)}/{len(by_number)}, elected {winners}/{g['seats']}, votes {total}/{valid})")
        out[gid] = {"status": doc["status"], "source": doc["source"], "published_at": doc["published_at"],
                    "valid_votes": valid, "candidates": sorted(rows, key=lambda r: r["number"])}
    return out


def merge(previous, new):
    races = dict(previous)
    for gid, r in new.items():
        old = races.get(gid)
        if old and old["status"] == "final" and r["status"] != "final":
            continue  # never downgrade a final result
        if old and datetime.fromisoformat(old["published_at"]) > datetime.fromisoformat(r["published_at"]) and old["status"] == r["status"]:
            continue
        races[gid] = r
    return races


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    out_path = Path(argv[argv.index("--out") + 1]) if "--out" in argv else DATA / "results-snapshot.json"
    if "--out" in argv:
        args.remove(str(out_path))
    groups, codes = roster()
    snap = json.loads(out_path.read_text()) if out_path.exists() else {"version": VERSION, "races": {}}
    races = snap.get("races") or {}
    now = datetime.now().astimezone()
    for f in args:
        races = merge(races, build_races(json.loads(Path(f).read_text()), groups, codes, now))
    snap = {"version": VERSION, "election_date": "2026-11-28", "source": "https://www.cec.gov.tw/",
            "status": "final" if races and all(r["status"] == "final" for r in races.values()) and len(races) == len(groups) else ("partial" if races else "not_published"),
            "races": dict(sorted(races.items())),
            "notice": "中選會官方結果；每筆逐一比對本站名冊號次與姓名。正式當選以中選會公告為準；不得以零票代替空值。" if races else "尚無官方結果資料；不得以零票代替空值。"}
    if "--check" in argv:
        print(len(races), "races valid")
        return
    out_path.write_text(json.dumps(snap, ensure_ascii=False, indent=1) + "\n")
    print(len(races), "races written to", out_path)


if __name__ == "__main__":
    main(sys.argv[1:])
