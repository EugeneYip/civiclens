"""Fetch the CEC vote-count pages (vote.cec.gov.tw) and write normalized inputs for
scripts/build_results_snapshot.py — one JSON file per race, each citing its own page.

The CEC count site publishes one HTML table per race: TC/<county>000000000000.html for
mayors and county magistrates, T1/<county><district>0000000000.html for councillors (codes
from the site's own tree file; indigenous districts use T2 lowland / T3 highland). Each table lists number, name, votes and the CEC's own vote
share, plus "已送投票所數/總投票所數" and "資料更新時間".

Rules: nothing is estimated. Valid votes are the sum of the listed candidates' votes, which
is what a single-vote race's valid-vote total is; every row's share is cross-checked against
the CEC's printed percentage and any mismatch aborts that race. Winners are recorded only
when the page itself marks them, and a race is "final" only when every station has reported
and the marked winners equal the seat count; otherwise it is "preliminary" with no winners.

Usage: python3 -I scripts/adapt_cec_vote.py OUT_DIR [--only TC|T1]
Downloaded pages are kept under OUT_DIR/raw and treated as untrusted text (parsed by regex).
"""
import concurrent.futures
import html
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = "https://vote.cec.gov.tw/2026-local/zh-TW/"
TREE = "https://vote.cec.gov.tw/2026-local/assets/def/tree-compiled.2026-local.min.json"


def fetch(url, dest):
    r = subprocess.run(["curl", "-s", "-f", "-m", "40", "--retry", "2", "-o", str(dest), url], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("fetch failed %s (curl %d)" % (url, r.returncode))
    return dest.read_text(encoding="utf-8", errors="replace")


def pages(tree):
    out = []
    for cid in tree["_AREAROOT"]["next"]:
        node = tree[cid]
        code, county = node["serial"]["c"], node["zh"]
        out.append(("chief", county, None, BASE + "TC/%s000000000000.html" % code))
        for o in node.get("overrides", []):
            if o["conditions"].get("ancestors") == ["qbd0"]:
                for y in o["mutations"]["next"]:
                    v = tree[y]
                    yc = v[2] if isinstance(v, list) else v["serial"]["y"]
                    prefix = "T1"  # indigenous districts reference a template that switches the prefix (T2 lowland, T3 highland)
                    if isinstance(v, list) and len(v) == 5 and isinstance(v[3], str):
                        for t in tree[v[3]].get("overrides", []):
                            if t["conditions"].get("ancestors") == ["c000"]:
                                prefix = t["mutations"]["serial"]["prefix"]
                    out.append(("council", county, int(yc), BASE + "%s/%s%s0000000000.html" % (prefix, code, yc)))
    return out


def cells(row):
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]


def parse(text, url):
    title = re.search(r'vote-table-header-title">.*?<b>(.*?)</b>', text, re.S)
    st = re.search(r"已送投票所數/總投票所數:\s*([\d,]+)\s*/\s*([\d,]+)", text)
    upd = re.search(r"資料更新時間:(?:&nbsp;|\s)*(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})", text)
    table = re.search(r"<table.*?</table>", text, re.S)
    if not (title and st and upd and table):
        raise ValueError("unexpected page layout: " + url)
    head = cells(re.search(r"<thead>(.*?)</thead>", table.group(0), re.S).group(1))
    idx = {h: i for i, h in enumerate(head)}
    for need in ("號次", "姓名", "得票數", "得票率%"):
        if need not in idx:
            raise ValueError("missing column %s: %s" % (need, url))
    mark = next((i for i, h in enumerate(head) if "當選" in h), None)
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", re.search(r"<tbody>(.*?)</tbody>", table.group(0), re.S).group(1), re.S):
        c = cells(tr)
        if len(c) != len(head):
            raise ValueError("row width mismatch: " + url)
        elected = None
        if mark is not None and c[mark]:
            elected = True
        if re.search(r'<img[^>]*(?:alt|title)="[^"]*當選', tr):
            elected = True
        rows.append({"number": int(c[idx["號次"]]), "name": c[idx["姓名"]], "votes": int(c[idx["得票數"]].replace(",", "")),
                     "pct": float(c[idx["得票率%"]]), "elected": elected})
    mo, dd, hh, mi = map(int, upd.groups())
    return {"title": re.sub(r"\s+", " ", html.unescape(title.group(1))).strip(), "reported": int(st.group(1).replace(",", "")),
            "total": int(st.group(2).replace(",", "")), "published_at": "2026-%02d-%02dT%02d:%02d:00+08:00" % (mo, dd, hh, mi), "rows": rows}


def race_doc(office, county, district, url, p, seats):
    total = sum(r["votes"] for r in p["rows"])
    for r in p["rows"]:
        share = round(r["votes"] / total * 100, 2) if total else 0.0
        if abs(share - r["pct"]) > 0.011:
            raise ValueError("vote share mismatch %s %s: %.2f vs CEC %.2f" % (url, r["name"], share, r["pct"]))
    winners = [r for r in p["rows"] if r["elected"]]
    final = p["total"] > 0 and p["reported"] == p["total"] and seats is not None and len(winners) == seats
    return {"source": url, "published_at": p["published_at"], "status": "final" if final else "preliminary",
            "races": [{"county": county, "office": office, "district": district, "valid_votes": total,
                       "stations": {"reported": p["reported"], "total": p["total"]},
                       "candidates": [{"number": r["number"], "name": r["name"], "votes": r["votes"],
                                       "elected": (bool(r["elected"]) if final else None)} for r in p["rows"]]}]}


def main(argv):
    out = Path(argv[0]); raw = out / "raw"; raw.mkdir(parents=True, exist_ok=True)
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    tree = json.loads(fetch(TREE, raw / "tree.json"))
    root = Path(__file__).resolve().parents[1]
    seats = {(c["name"], d["number"]): d["seats"] for c in json.loads((root / "data/council-districts.json").read_text())["counties"] for d in c["districts"]}
    todo = [p for p in pages(tree) if not only or ("/%s/" % only) in p[3]]
    if len(todo) != 243 and not only:
        raise SystemExit("expected 243 races (22 chief + 221 council), got %d" % len(todo))

    def work(item):
        office, county, district, url = item
        text = fetch(url, raw / (url.rsplit("/", 2)[-2] + "_" + url.rsplit("/", 1)[-1]))
        p = parse(text, url)
        doc = race_doc(office, county, district, url, p, 1 if office == "chief" else seats.get((county, district)))
        name = "%s_%s_%s.json" % (county, office, district or 0)
        (out / name).write_text(json.dumps(doc, ensure_ascii=False))
        return p["reported"], p["total"], doc["status"]

    done, errors, stats = 0, [], {"preliminary": 0, "final": 0, "reported": 0, "total": 0}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for item, fut in [(i, ex.submit(work, i)) for i in todo]:
            try:
                rep, tot, status = fut.result()
                done += 1; stats[status] += 1
                if item[0] == "chief":
                    stats["reported"] += rep; stats["total"] += tot
            except Exception as e:  # keep going; report every failure
                errors.append("%s %s %s: %s" % (item[1], item[0], item[2] or "", e))
    print(json.dumps({"races": done, "errors": len(errors), **stats}, ensure_ascii=False))
    for e in errors:
        print("ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
