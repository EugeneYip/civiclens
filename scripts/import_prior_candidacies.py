"""Link 2026 candidates to their own 2022 (民國111年) candidacy in the CEC election database.

A 2026 candidate is linked to a 2022 county-chief or council candidacy only when all of these
match: county, name (whitespace and middle-dot variants normalised; for names with a romanised
Indigenous part, the Chinese part), sex and birth year (2026 values from the CEC 2026 election
site, 2022 values from the CEC database).  A name match that fails sex or birth year is not
linked; if several 2022 rows match, none is linked.  Nothing is inferred from party or district.

Usage: python3 scripts/import_prior_candidacies.py --cache DIR [--offline]
(DIR is the same cache used by scripts/import_historical_results.py.)
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_historical_results as hist  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "prior-candidacies-2022.json"
VERSION = "0.1.44"
SEX = {"男": "1", "女": "2"}


def norm(name):
    return re.sub(r"[‧．·•・･.\s]", "", name).replace("台", "臺")


def chinese_part(name):
    return name.split(" ")[0] if re.search(r"[A-Za-z]", name) else name


def build(cache, offline):
    counties = json.loads((ROOT / "data" / "election.json").read_text())["counties"]
    by_name = {c["name"]: c["code"] for c in counties}
    names = {c["code"]: c["name"] for c in counties}
    official = json.loads((ROOT / "data" / "cec-official-2026.json").read_text())["records"]
    groups = [g for f in ("published-roster.json", "national-roster-supplement.json") for g in json.loads((ROOT / "data" / f).read_text())["districts"]]
    rows, files, area = [], {}, {}
    for subject, legis, theme, label, date in hist.CHIEF_THEMES:
        t = hist.fetch(f"tickets/ELC/{subject}/{legis}/{theme}/C/00_000_00_000_0000.json", cache, offline)
        p = hist.fetch(f"profiles/ELC/{subject}/{legis}/{theme}/C/00_000_00_000_0000.json", cache, offline)
        if not t or not p:
            raise SystemExit("missing chief data for " + label)
        files[t["url"]] = t["sha256"]
        for prof in hist.rows(p):
            area[(prof["prv_code"], prof["city_code"])] = by_name[prof["area_name"]]
        for r in hist.rows(t):
            rows.append((label, date, t["url"], r, "chief"))
    for code, (prv, city) in sorted({v: k for k, v in area.items()}.items()):
        subject = "T1" if prv in hist.MUNICIPAL else "T2"
        for s, legis, theme, label in hist.COUNCIL_THEMES:
            if s != subject:
                continue
            t = hist.fetch(f"tickets/ELC/{s}/{legis}/{theme}/A/{prv}_{city}_00_000_0000.json", cache, offline)
            if not t:
                continue
            files[t["url"]] = t["sha256"]
            kind = "直轄市議員" if s == "T1" else "縣市議員"
            for r in hist.rows(t):
                rows.append((f"111年{kind}選舉（{label.split('｜')[1]}）", "2022-11-26", t["url"], r, "council"))
    index = defaultdict(list)
    for label, date, url, r, office in rows:
        code = area.get((r["prv_code"], r["city_code"])) or area.get((r["ris_prv_code"], r["ris_city_code"]))
        if code:
            index[(code, norm(r["cand_name"]))].append((label, date, url, r, office, code))
    records, rejected = {}, []
    for g in groups:
        for c in g["candidates"]:
            o = official.get(c["id"]) or {}
            hits = index.get((g["county"], norm(chinese_part(c["name"]))), [])
            if not hits:
                continue
            good = [h for h in hits if h[3]["cand_sex"] == SEX.get(o.get("gender")) and h[3]["cand_birthyear"] == str(o.get("birth_year"))]
            if len(good) != 1:
                rejected.append({"id": c["id"], "reason": "sex_or_birth_year_differs" if not good else "several_matches"})
                continue
            label, date, url, r, office, code = good[0]
            area_name = r["area_name"]
            race = names[code] + ("長" if office == "chief" and names[code].endswith(("縣", "市")) else "")
            if office == "council":
                race = names[code] + "議員" + re.sub(r"第0*(\d+)選舉區", r"第\1選舉區", area_name)
            records[c["id"]] = {
                "election": label, "vote_date": date, "office": office, "race": race,
                "number": r["cand_no"], "party": hist.party(r["party_name"]),
                "votes": r["ticket_num"], "percent": r["ticket_percent"],
                "elected": r["is_victor"] in hist.VICTOR_MARKS, "incumbent": r["is_current"] == "Y",
                "source": url,
            }
    return {
        "version": VERSION,
        "election": "111年地方公職人員選舉（直轄市長、縣市長、直轄市議員、縣市議員）",
        "method": "以縣市、姓名、性別及出生年四項與中選會選舉資料庫一致者才連結；同名但性別或出生年不同者不連結。僅涵蓋同一縣市內的首長與議員選舉，不含鄉鎮市及村里選舉。",
        "source": {"database": "https://db.cec.gov.tw/", "files": [{"url": u, "sha256": h} for u, h in sorted(files.items())]},
        "stats": {"linked": len(records), "elected_2022": sum(r["elected"] for r in records.values()), "rejected_name_only": len(rejected)},
        "rejected": rejected,
        "records": dict(sorted(records.items())),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    data = build(a.cache, a.offline)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps(data["stats"], ensure_ascii=False))


if __name__ == "__main__":
    main()
