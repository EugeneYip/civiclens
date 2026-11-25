"""Build the party nomination summary used by the results page.

The precedence mirrors scripts/explorer.js partyLabel():
official roster party -> CEC 2026 election-site party -> bulletin transcription -> registration data -> registration
secondary transcription.  Candidates without any of these remain "pending"; they are
never assigned to a party by inference.  Seats are never estimated here: elected seats
are computed in the browser only from validated final results.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
VERSION = "0.1.26"
NONE_LABELS = {"無", "無黨籍", "未經政黨推薦", "無黨籍及未經政黨推薦"}
TIERS = ("official", "cec_official", "bulletin", "registration", "registration_secondary")
OUTPUT = DATA / "party-summary.json"


def load(name):
    return json.loads((DATA / name).read_text())


def normalize(party):
    party = re.sub(r"\s+", "", party)
    return "無" if party in NONE_LABELS else party


def resolve(row, bulletin, supplement, cec):
    b = bulletin.get(row["id"])
    bulletin_party = None
    if b and b.get("name") == row["name"] and b.get("number") == row["number"] and b.get("status") == "secondary_bulletin_transcription":
        bulletin_party = b.get("party")
    x = supplement.get(row["id"])
    secondary = None
    if (row.get("party") is None and row.get("registration_party") is None and x
            and x.get("name") == row["name"] and x.get("status") == "registration_secondary_exact_match"):
        secondary = x.get("party")
    cec_party = (cec.get(row["id"]) or {}).get("party")
    for tier, value in zip(TIERS, (row.get("party"), cec_party, bulletin_party, row.get("registration_party"), secondary)):
        if value is not None and str(value).strip():
            return normalize(str(value)), tier
    return None, "pending"


def build():
    groups = [g for f in ("published-roster.json", "national-roster-supplement.json") for g in load(f)["districts"]]
    hold = set(load("bulletin-quarantine.json")["ids"])
    bulletin = {k: v for k, v in load("bulletin-facts.json")["records"].items() if k not in hold}
    supplement = load("candidate-parties.json")["records"]
    cec = load("cec-official-2026.json")["records"]
    districts = load("council-districts.json")
    seats = {c["code"]: c["seats"] for c in districts["counties"]}
    if len(groups) != 243 or len({g["id"] for g in groups}) != 243:
        raise SystemExit("roster must contain 243 unique races")
    candidates = {}
    counts = defaultdict(lambda: defaultdict(Counter))
    tiers = defaultdict(lambda: defaultdict(Counter))
    for g in groups:
        for row in g["candidates"]:
            party, tier = resolve(row, bulletin, supplement, cec)
            if row["id"] in candidates:
                raise SystemExit("duplicate candidate id " + row["id"])
            candidates[row["id"]] = [party, tier]
            key = party or "待核"
            for scope in (g["county"], "all"):
                counts[scope][g["office"]][key] += 1
                tiers[scope][g["office"]][tier] += 1

    def table(scope, office):
        rows = sorted(counts[scope][office].items(), key=lambda kv: (kv[0] in ("無", "待核"), -kv[1], kv[0]))
        return {
            "candidates": sum(counts[scope][office].values()),
            "parties": [{"party": p, "candidates": n} for p, n in rows],
            "tiers": {t: tiers[scope][office][t] for t in TIERS + ("pending",)},
        }

    county_codes = sorted({g["county"] for g in groups})
    summary = {
        "version": VERSION,
        "method": "依本站候選人頁相同順序取用政黨欄位：名冊推薦政黨、中選會115年選舉專區官方資料、公報推薦政黨轉錄、登記資料、登記資料民間轉錄；皆無者列為待核，不推定政黨。候選人數為提名／推薦或登記標示，不代表當選席次或目前黨籍。",
        "tier_labels": {
            "official": "名冊推薦政黨",
            "cec_official": "中選會選舉專區官方資料",
            "bulletin": "公報推薦政黨轉錄（第三方，未逐筆覆核）",
            "registration": "登記資料",
            "registration_secondary": "登記資料民間轉錄",
            "pending": "政黨欄位待核",
        },
        "seats": {"chief": len(county_codes), "council": districts["seats"], "by_county": {c: {"chief": 1, "council": seats[c]} for c in county_codes}},
        "national": {o: table("all", o) for o in ("chief", "council")},
        "counties": {c: {o: table(c, o) for o in ("chief", "council")} for c in county_codes},
        "candidates": dict(sorted(candidates.items())),
    }
    return summary


def main():
    summary = build()
    text = json.dumps(summary, ensure_ascii=False, separators=(",", ":")) + "\n"
    if "--check" in sys.argv:
        if OUTPUT.read_text() != text:
            raise SystemExit("data/party-summary.json is stale; run scripts/build_party_summary.py")
        return
    OUTPUT.write_text(text)
    n = summary["national"]
    print("chief", n["chief"]["candidates"], n["chief"]["tiers"], "council", n["council"]["candidates"], n["council"]["tiers"])


if __name__ == "__main__":
    main()
