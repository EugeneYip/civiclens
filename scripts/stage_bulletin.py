"""Stage 2026 bulletin text from a pinned public SQLite source; never publish automatically."""
import argparse
import collections
import hashlib
import json
import sqlite3
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "e2791191fdd52681703dde9b6a5486b5e0ceca45"
URL = f"https://raw.githubusercontent.com/Yaochieh/taiwan-election/{COMMIT}/data/db.sqlite"
ORIGIN = f"https://github.com/Yaochieh/taiwan-election/tree/{COMMIT}"
MAX_BYTES = 50 * 1024 * 1024

def official_url(s):
    try:
        u = urlparse(s)
        return u.scheme == "https" and u.netloc in ("eebulletin.cec.gov.tw", "bulletin.cec.gov.tw", "web.cec.gov.tw") and u.path.lower().endswith(".pdf")
    except (TypeError, ValueError):
        return False

def strings(s):
    try:
        a = json.loads(s or "[]")
    except (ValueError, TypeError):
        return []
    return [x.strip() for x in a if isinstance(x, str) and x.strip()] if isinstance(a, list) else []

def roster_index(root):
    names = {c["code"]: c["name"] for c in json.loads((root/"data/gazettes.json").read_text())["counties"]}
    index = collections.defaultdict(list)
    for f in ("published-roster", "national-roster-supplement"):
        for d in json.loads((root/"data"/f"{f}.json").read_text())["districts"]:
            county = names[d["county"]]
            district = county if d["office"] == "chief" else f"{county}第{d['number']}選舉區"
            for r in d["candidates"]:
                index[(d["office"], district, r["number"], r["name"])].append(r)
    return index

def stage(conn, index):
    records, excluded = {}, []
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""SELECT c.name, c.district, b.* FROM candidate_bulletin_profiles b
      JOIN candidates c USING(candidate_id)
      WHERE b.election_id BETWEEN 77 AND 82 AND c.election_id=b.election_id""").fetchall()
    for b in rows:
        office = "chief" if b["election_id"] in (77, 78) else "council"
        key = (office, b["district"], b["ballot_no"], b["name"])
        hit = index.get(key, [])
        if len(hit) != 1 or hit[0].get("source_conflict") or not official_url(b["source_url"]) or not isinstance(b["source_page"], int) or b["source_page"] < 1:
            excluded.append({"name": b["name"], "district": b["district"], "number": b["ballot_no"], "reason": "identity_or_source_not_verified"})
            continue
        r = hit[0]
        if r["id"] in records:
            raise ValueError("duplicate source identity " + r["id"])
        policy = []
        for p in conn.execute("""SELECT content, content_raw, source_url, note FROM platforms
            WHERE candidate_id=? AND election_id=? ORDER BY seq""", (b["candidate_id"], b["election_id"])):
            if p["source_url"] == b["source_url"] and p["content"] and p["content"] == p["content_raw"] and "公報原文照抄" in (p["note"] or ""):
                policy.append(p["content"])
        records[r["id"]] = {"name": r["name"], "number": r["number"], "district": b["district"],
            "source_url": b["source_url"], "source_page": b["source_page"], "source_kind": b["source_kind"],
            "party_raw": b["party_raw"], "education": strings(b["education"]), "career": strings(b["career"]),
            "policy": policy, "status": "review_required"}
    return {"source": {"name": "正至 · 台灣選舉資訊平台", "repository": ORIGIN, "database": URL},
        "notice": "僅供覆核；第三方公報轉錄未經本站逐筆核對，禁止自動發布。未匯入出生資料或圖片。",
        "stats": {"source_rows": len(rows), "matched": len(records), "excluded": len(excluded),
                  "education": sum(bool(r["education"]) for r in records.values()),
                  "career": sum(bool(r["career"]) for r in records.values()),
                  "policy": sum(bool(r["policy"]) for r in records.values()),
                  "party": sum(bool(r["party_raw"]) for r in records.values())},
        "records": records, "excluded": excluded}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, help="Local SQLite snapshot; default downloads pinned public source")
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    if a.output.resolve().is_relative_to((ROOT/"data").resolve()):
        parser.error("Staging output must not be inside the public data directory")
    with tempfile.TemporaryDirectory() as temp:
        db = a.db or Path(temp)/"source.sqlite"
        if not a.db:
            req = urllib.request.Request(URL, headers={"User-Agent": "CivicLens-bulletin-review"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read(MAX_BYTES+1)
            if len(payload) > MAX_BYTES or not payload.startswith(b"SQLite format 3\x00"):
                raise ValueError("invalid or oversized SQLite snapshot")
            db.write_bytes(payload)
        if db.stat().st_size > MAX_BYTES:
            raise ValueError("oversized SQLite snapshot")
        with sqlite3.connect(db.resolve().as_uri()+"?mode=ro&immutable=1", uri=True) as conn:
            conn.execute("PRAGMA query_only=ON")
            result = stage(conn, roster_index(ROOT))
        result["source"]["sha256"] = hashlib.sha256(db.read_bytes()).hexdigest()
        if result["stats"]["matched"] < 1000:
            raise ValueError(f"Unexpectedly low match coverage: {result['stats']}")
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(result, ensure_ascii=False, indent=1)+"\n")
        print(json.dumps(result["stats"], ensure_ascii=False))

if __name__ == "__main__":
    main()
