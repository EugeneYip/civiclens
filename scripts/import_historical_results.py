"""Import official 2022 (民國111年) local election results from the CEC election database.

Usage:
  python3 scripts/import_historical_results.py --cache DIR          # download into DIR, then build
  python3 scripts/import_historical_results.py --cache DIR --offline # build from DIR only

Only the CEC election database (db.cec.gov.tw) static JSON files are used.  Every file is
recorded with its URL and SHA-256.  The output is a historical reference for comparison; it
is not a prediction and does not attribute a previous office-holder's record to any 2026
candidate.
"""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "historical-results-2022.json"
BASE = "https://db.cec.gov.tw/static/elections/data/"
VERSION = "0.1.25"
NONE_PARTY = "無黨籍及未經政黨推薦"
# subject, legislator type, theme id, label, vote date
CHIEF_THEMES = [
    ("C1", "00", "05cc7b904c7a30cc7c88d5b10898c98e", "111年直轄市長選舉", "2022-11-26"),
    ("C2", "00", "63615098f5afa8ec53159c4a86fc01d3", "111年縣市長選舉", "2022-11-26"),
    ("C2", "00", "1275d73551f2c0caf202e803b1766057", "111年嘉義市長重行選舉", "2022-12-18"),
]
COUNCIL_THEMES = [
    ("T1", "T1", "25e12c45f9f5641aab4193598d5aff6e", "直轄市議員｜區域"),
    ("T1", "T2", "44cf35b1708568b94bb3b4c38a3fc74c", "直轄市議員｜平地原住民"),
    ("T1", "T3", "699b1ece9739edf4ec4662cea25a0bb3", "直轄市議員｜山地原住民"),
    ("T2", "T1", "72976331a1ea6b85cfb1ed3380ae5f35", "縣市議員｜區域"),
    ("T2", "T2", "c8f4dc82f282bed4ebcdf0f52552cf58", "縣市議員｜平地原住民"),
    ("T2", "T3", "4ad215cf6c4ef28b25278bd1a13bc7bf", "縣市議員｜山地原住民"),
]
MUNICIPAL = {"63", "64", "65", "66", "67", "68"}
VICTOR_MARKS = {"*", "!"}  # both are elected marks in the CEC database


def fetch(path, cache, offline):
    target = cache / path.replace("/", "__")
    if not target.exists():
        if offline:
            return None
        url = BASE + path
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "civic-data-import/1.0"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    target.write_bytes(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    target.write_bytes(b"404")
                    break
                time.sleep(2 + attempt * 2)
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(2 + attempt * 2)
        else:
            raise SystemExit("download failed: " + url)
        time.sleep(0.4)
    raw = target.read_bytes()
    if raw == b"404":
        return None
    return {"url": BASE + path, "sha256": hashlib.sha256(raw).hexdigest(), "data": json.loads(raw)}


def rows(doc):
    (key, value), = doc["data"].items()
    return value


def party(name):
    return "無" if name == NONE_PARTY else name


def build(cache, offline):
    counties = json.loads((ROOT / "data" / "election.json").read_text())["counties"]
    by_name = {c["name"]: c["code"] for c in counties}
    files = []
    out = {c["code"]: {"name": c["name"]} for c in counties}
    area_codes = {}
    for subject, legis, theme, label, date in CHIEF_THEMES:
        t = fetch(f"tickets/ELC/{subject}/{legis}/{theme}/C/00_000_00_000_0000.json", cache, offline)
        p = fetch(f"profiles/ELC/{subject}/{legis}/{theme}/C/00_000_00_000_0000.json", cache, offline)
        if not t or not p:
            raise SystemExit("missing chief data for " + label)
        files += [{"url": t["url"], "sha256": t["sha256"]}, {"url": p["url"], "sha256": p["sha256"]}]
        for prof in rows(p):
            code = by_name[prof["area_name"]]
            if "chief" in out[code] and theme != "1275d73551f2c0caf202e803b1766057":
                continue
            area_codes[code] = (prof["prv_code"], prof["city_code"])
            cands = sorted((r for r in rows(t) if r["area_name"] == prof["area_name"]), key=lambda r: r["cand_no"])
            out[code]["chief"] = {
                "election": label,
                "vote_date": date,
                "valid_votes": prof["valid_ticket"],
                "invalid_votes": prof["invalid_ticket"],
                "total_votes": prof["vote_ticket"],
                "electors": prof["votable_population"],
                "turnout_percent": prof["vote_to_elect"],
                "candidates": [{
                    "number": r["cand_no"], "name": r["cand_name"], "party": party(r["party_name"]),
                    "votes": r["ticket_num"], "percent": r["ticket_percent"], "elected": r["is_victor"] in VICTOR_MARKS,
                    "incumbent": r["is_current"] == "Y",
                } for r in cands],
            }
    if set(area_codes) != set(out):
        raise SystemExit("chief data does not cover all 22 counties")
    for code, (prv, city) in sorted(area_codes.items()):
        subject = "T1" if prv in MUNICIPAL else "T2"
        council = {"seats": 0, "candidates": 0, "districts": 0, "valid_votes": 0, "parties": defaultdict(lambda: Counter()), "types": []}
        for s, legis, theme, label in COUNCIL_THEMES:
            if s != subject:
                continue
            t = fetch(f"tickets/ELC/{s}/{legis}/{theme}/A/{prv}_{city}_00_000_0000.json", cache, offline)
            p = fetch(f"profiles/ELC/{s}/{legis}/{theme}/A/{prv}_{city}_00_000_0000.json", cache, offline)
            if not t:
                continue
            if not p:
                raise SystemExit("missing council profile for " + code + " " + label)
            files += [{"url": t["url"], "sha256": t["sha256"]}, {"url": p["url"], "sha256": p["sha256"]}]
            profs = rows(p)
            elected = sum(x["elected_num"] for x in profs)
            cand_rows = rows(t)
            winners = sum(r["is_victor"] in VICTOR_MARKS for r in cand_rows)
            if winners != elected or len(cand_rows) != sum(x["cand_num"] for x in profs):
                raise SystemExit("council totals do not reconcile for " + code + " " + label)
            council["types"].append(label.split("｜")[1])
            council["seats"] += elected
            council["candidates"] += len(cand_rows)
            council["districts"] += len(profs)
            council["valid_votes"] += sum(x["valid_ticket"] for x in profs)
            for r in cand_rows:
                c = council["parties"][party(r["party_name"])]
                c["candidates"] += 1
                c["seats"] += r["is_victor"] in VICTOR_MARKS
                c["votes"] += r["ticket_num"]
        council["parties"] = [
            {"party": k, "candidates": v["candidates"], "seats": v["seats"], "votes": v["votes"]}
            for k, v in sorted(council["parties"].items(), key=lambda kv: (kv[0] == "無", -kv[1]["seats"], -kv[1]["votes"], kv[0]))
        ]
        out[code]["council"] = council

    national_chief = Counter(c["party"] for v in out.values() for c in v["chief"]["candidates"] if c["elected"])
    national_council = defaultdict(Counter)
    for v in out.values():
        for x in v["council"]["parties"]:
            for k in ("candidates", "seats", "votes"):
                national_council[x["party"]][k] += x[k]
    unique = {}
    for f in files:
        unique[f["url"]] = f["sha256"]
    return {
        "version": VERSION,
        "election": "111年地方公職人員選舉",
        "vote_date": "2022-11-26",
        "notice": "中選會選舉資料庫正式結果；嘉義市長為111年12月18日重行選舉。僅供歷屆比較，不代表本屆預測，亦不將前任施政或得票歸屬於本屆候選人。議員含區域、平地及山地原住民選區；不含鄉鎮市及山地原住民區。資料庫當選標記「*」與「!」均以當選計，「!」之意義依中選會資料庫，本站未另行判讀。",
        "source": {"database": "https://db.cec.gov.tw/", "files": [{"url": u, "sha256": h} for u, h in sorted(unique.items())]},
        "national": {
            "chief_seats": [{"party": k, "seats": n} for k, n in sorted(national_chief.items(), key=lambda kv: (kv[0] == "無", -kv[1], kv[0]))],
            "council_seats": sum(v["council"]["seats"] for v in out.values()),
            "council_parties": [
                {"party": k, "candidates": v["candidates"], "seats": v["seats"], "votes": v["votes"]}
                for k, v in sorted(national_council.items(), key=lambda kv: (kv[0] == "無", -kv[1]["seats"], -kv[1]["votes"], kv[0]))
            ],
        },
        "counties": dict(sorted(out.items())),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    data = build(a.cache, a.offline)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    n = data["national"]
    print("chief", n["chief_seats"], "council seats", n["council_seats"], "files", len(data["source"]["files"]))


if __name__ == "__main__":
    main()
