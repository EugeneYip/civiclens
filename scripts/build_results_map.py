"""Build data/results-map.json for the home-page county map from data/results-snapshot.json.

For each of the 22 mayor/magistrate races: the candidate with the most official votes so far
(no estimate; a tie means no leader), their party, vote share, runner-up, stations reported and
status. Status is "final" only when the CEC marked winners (snapshot status final); otherwise
"all_reported" when every station has reported, else "counting". The page words these as
當選 / 得票最高（中選會尚未標示當選） / 開票中領先.

Usage: python3 scripts/build_results_map.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name):
    return json.loads((DATA / name).read_text())


def main():
    snap = load("results-snapshot.json"); parties = load("party-summary.json")["candidates"]
    geo = load("taiwan-counties-map.json")["counties"]
    by_name = {v["name"]: k for k, v in geo.items()}
    counties, rep_sum, tot_sum, latest = [], 0, 0, None
    for c in load("election.json")["counties"]:
        cec = by_name.get(c["name"])
        if not cec:
            raise SystemExit("no map shape for " + c["name"])
        r = snap["races"].get(c["code"] + "-chief")
        row = {"code": c["code"], "cec": cec, "name": c["name"], "status": "none"}
        if r:
            st = r.get("stations") or {}
            total = sum(v["votes"] for v in r["candidates"])
            ranked = sorted(r["candidates"], key=lambda v: -v["votes"])
            share = lambda v: round(v["votes"] / total * 100, 2) if total else 0.0
            pick = lambda v: {"id": v["id"], "name": v["name"], "party": parties.get(v["id"], ["待核"])[0], "votes": v["votes"], "share": share(v)}
            row.update(source=r["source"], published_at=r["published_at"], stations=st, valid=total)
            if r["status"] == "final":
                won = [v for v in r["candidates"] if v.get("elected")]
                row.update(status="final", leader=pick(won[0]) if len(won) == 1 else None)
            else:
                row["status"] = "all_reported" if st and st.get("reported") == st.get("total") else "counting"
                tie = len(ranked) > 1 and ranked[0]["votes"] == ranked[1]["votes"]
                row["leader"] = pick(ranked[0]) if total and not tie else None
            if len(ranked) > 1 and total:
                row["runner_up"] = pick(ranked[1])
            rep_sum += st.get("reported", 0); tot_sum += st.get("total", 0)
            latest = max(latest or r["published_at"], r["published_at"])
        counties.append(row)
    out = {"version": "0.1.82", "published_at": latest, "stations": {"reported": rep_sum, "total": tot_sum},
           "note": "依中選會計票網站各縣市長得票數；未標示當選前僅顯示目前得票最高者，當選以中選會公告為準。",
           "counties": counties}
    (DATA / "results-map.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(len(counties), "counties;", sum(1 for c in counties if c.get("leader")), "with a leader; stations", rep_sum, "/", tot_sum)


if __name__ == "__main__":
    main()
