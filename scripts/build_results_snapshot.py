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
     "stations": {"reported": 12, "total": 1790},      # optional: polling stations counted so far
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
    return re.sub(r"[‧．·•・･.]", "‧", re.sub(r"\s+", "", name)).replace("台", "臺").replace("黄", "黃")


HAN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
# Reviewed exceptions where CEC systems spell a name differently. Key: (race id, number).
# 09-council-8 No. 9: the CEC candidate registry and the printed gazette read 洪建興;
# the CEC vote-count site reads 洪健興. Number, district and gender agree.
ALIASES = {("09-council-8", 9): ("洪建興", "洪健興")}


def same_person(gid, number, roster_name, source_name):
    """True when a CEC count-page name denotes the roster candidate with that number."""
    a, b = norm(roster_name), norm(source_name)
    if a == b:
        return True
    if ALIASES.get((gid, number)) == (roster_name, source_name):
        return True
    # Indigenous candidates: one source may append the romanized name; the Han part must match
    # exactly and the remainder must be Latin letters, spaces, dots or apostrophes only.
    ha, hb = "".join(HAN.findall(a)), "".join(HAN.findall(b))
    rest = lambda n, h: n[len(h):] if n.startswith(h) else None
    ra, rb = rest(a, ha), rest(b, hb)
    latin = re.compile(r"^[A-Za-z‧'’ʼ\-]*$")
    return bool(ha) and ha == hb and ra is not None and rb is not None and latin.match(ra) and latin.match(rb)


def load(name):
    return json.loads((DATA / name).read_text())


def roster():
    groups = [g for f in ("published-roster.json", "national-roster-supplement.json") for g in load(f)["districts"]]
    codes = {c["name"]: c["code"] for c in load("election.json")["counties"]}
    return {g["id"]: g for g in groups}, codes


def official(url):
    u = urlparse(url)
    return u.scheme == "https" and u.hostname in OFFICIAL_HOSTS and not u.username and not u.password and not u.port


def project(rows, seats, women_reserved):
    """Projected winners from COMPLETE counts (every station reported), applying the women's
    reserved seats rule of the Civil Servants Election and Recall Act art. 68: the top `seats`
    by votes win; if fewer than `women_reserved` of them are women, the women with the most votes
    among the rest replace the lowest-ranked men. Returns (sorted ids, None) or (None, reason)
    when a tie at any cutoff makes the outcome depend on the statutory lot (抽籤).
    rows: [{"id", "votes", "gender"}]."""
    if seats < 1 or not rows:
        return None, "no seats"
    ranked = sorted(rows, key=lambda r: -r["votes"])
    if len(ranked) > seats and ranked[seats - 1]["votes"] == ranked[seats]["votes"]:
        return None, "tie at the seat cutoff"
    win = ranked[:seats]
    short = women_reserved - sum(r["gender"] == "女" for r in win)
    if short > 0:
        outside = [r for r in ranked[seats:] if r["gender"] == "女"]
        take = outside[:short]
        if len(outside) > short and short > 0 and outside[short - 1]["votes"] == outside[short]["votes"]:
            return None, "tie among women for a reserved seat"
        men = [r for r in win if r["gender"] != "女"]
        drop = men[len(men) - len(take):] if take else []
        if take and len(men) > len(take) and men[len(men) - len(take) - 1]["votes"] == drop[0]["votes"]:
            return None, "tie among men displaced by a reserved seat"
        ids = {r["id"] for r in drop}
        win = [r for r in win if r["id"] not in ids] + take
    return sorted(r["id"] for r in win), None


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
        rows, seen, total, winners, gender_of = [], set(), 0, 0, {}
        if race.get("seats_cec") is not None and race["seats_cec"] != g["seats"]:
            raise ResultError(f"{gid}: CEC seat count {race['seats_cec']} differs from roster {g['seats']}")
        for v in race["candidates"]:
            c = by_number.get(v["number"])
            if not c or not same_person(gid, v["number"], c["name"], v["name"]):
                raise ResultError(f"{gid}: number/name {v['number']} {v['name']} not in roster")
            if c["id"] in seen:
                raise ResultError(f"{gid}: duplicate candidate {c['id']}")
            if not isinstance(v["votes"], int) or isinstance(v["votes"], bool) or v["votes"] < 0:
                raise ResultError(f"{gid}: invalid votes for {c['id']}")
            if v.get("gender") not in (None, "男", "女"):
                raise ResultError(f"{gid}: unexpected gender {v.get('gender')!r}")
            gender_of[c["id"]] = v.get("gender")
            row = {"id": c["id"], "name": c["name"], "number": c["number"], "votes": v["votes"]}
            if (gid, v["number"]) in ALIASES:
                row["source_name"] = v["name"]  # shown beside the roster name on the results page
            if final:
                if not isinstance(v.get("elected"), bool):
                    raise ResultError(f"{gid}: final results need an elected flag for {c['id']}")
                row["elected"] = v["elected"]
                winners += v["elected"]
                if v.get("mark") is not None:  # CEC 註記: ● = elected on a women's reserved seat, - = displaced by one
                    if v["mark"] not in ("◎", "●", "-", "＜") or (v["mark"] in ("◎", "●")) != v["elected"]:
                        raise ResultError(f"{gid}: inconsistent CEC mark {v['mark']!r} for {c['id']}")
                    if v["mark"] in ("●", "-", "＜"):
                        row["mark"] = v["mark"]
            elif v.get("elected") is not None:
                raise ResultError(f"{gid}: preliminary results must not mark winners")
            seen.add(c["id"]); total += v["votes"]; rows.append(row)
        valid = race.get("valid_votes")
        if valid is not None and (not isinstance(valid, int) or total > valid):
            raise ResultError(f"{gid}: candidate votes exceed valid votes")
        if final and (len(seen) != len(by_number) or winners != g["seats"] or valid != total):
            raise ResultError(f"{gid}: final race incomplete or inconsistent (candidates {len(seen)}/{len(by_number)}, elected {winners}/{g['seats']}, votes {total}/{valid})")
        st = race.get("stations")
        if st is not None:
            rep, tot = st.get("reported"), st.get("total")
            if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (rep, tot)) or rep > tot or tot == 0:
                raise ResultError(f"{gid}: invalid station counts {st!r}")
            if final and rep != tot:
                raise ResultError(f"{gid}: final race with stations still uncounted ({rep}/{tot})")
            st = {"reported": rep, "total": tot}
        out[gid] = {"status": doc["status"], "source": doc["source"], "published_at": doc["published_at"],
                    "valid_votes": valid, "candidates": sorted(rows, key=lambda r: r["number"])}
        if st is not None:
            out[gid]["stations"] = st
        # Projected winners ("預計當選") only from complete counts, while the CEC has not marked winners.
        # Not for indigenous districts: their women's reserved seats are pooled across all of the county's
        # lowland (or highland) districts, so a per-district projection is wrong (checked against the
        # CEC's own marks on 2026-11-29: the rule matched all 238 other races and missed 5 indigenous ones).
        if not final and "原住民" not in (g.get("scope") or "") and st is not None and st["reported"] == st["total"] and len(seen) == len(by_number) and all(gender_of.get(r["id"]) for r in rows):
            ids, why = project([{"id": r["id"], "votes": r["votes"], "gender": gender_of[r["id"]]} for r in rows], g["seats"], int(race.get("women_reserved") or 0))
            out[gid]["projection"] = {"basis": "complete_counts", "women_reserved": int(race.get("women_reserved") or 0)}
            if ids:
                out[gid]["projected"] = ids
            else:
                out[gid]["projection"]["undetermined"] = why
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
