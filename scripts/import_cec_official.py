"""Import the official CEC 2026 candidate list and map display photos and party emblems.

Sources
- CEC 2026 election site JSON (info.cec.gov.tw/vote2026/static/json/cand/{C1,T}/{prvCityCode}.json):
  official ballot number, name, recommended party, gender, birth year, place of origin and the
  official registration-photo path.  CEC photo files send Cross-Origin-Resource-Policy:
  same-site, so browsers cannot display them on another site; they are kept as source links.
- 2026 民間版選舉公報 (gazette2026.taiwangogo.tw) district pages: WebP conversions of the same
  CEC registration photos and MOI-registered party emblems, which allow cross-origin display.
  Its text/data are CC BY 4.0; photos and emblems are outside that licence and are only linked,
  never copied.

Every district must match one-to-one on ballot number and whitespace-normalized name for both
sources; otherwise that district is left out and reported.
"""
import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "cec-official-2026.json"
VERSION = "0.1.26"
CEC = "https://info.cec.gov.tw/vote2026/static"
GAZ = "https://gazette2026.taiwangogo.tw"
NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
NONE_PARTY = {"無", "無黨籍", "無黨籍及未經政黨推薦", "未經政黨推薦"}


def zh_number(s):
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + NUM[s[1]]
    if "十" in s:
        a, _, b = s.partition("十")
        return NUM[a] * 10 + (NUM[b] if b else 0)
    return NUM[s]


SEPARATORS = re.compile(r"[‧．·•・･.]")


def norm(s):
    """Whitespace-free, 臺/台-unified, with Indigenous name separators unified."""
    return SEPARATORS.sub("‧", re.sub(r"\s+", "", s or "").replace("台", "臺"))


def same_person_name(roster_name, source_name):
    """Exact after normalization, or one side omits only a romanized Indigenous name."""
    a, b = norm(roster_name), norm(source_name)
    if a == b:
        return True
    short, long = sorted((a, b), key=len)
    return long.startswith(short) and re.search(r"[\u4e00-\u9fff]", short) is not None and re.fullmatch(r"[A-Za-zʼ'‧\-]+", long[len(short):]) is not None


def party_norm(p):
    p = re.sub(r"\s+", "", p or "")
    return "無" if p in NONE_PARTY else p


def fetch(url, cache, offline, binary=False):
    target = cache / hashlib.sha256(url.encode()).hexdigest()
    if not target.exists():
        if offline:
            raise SystemExit("missing cached source: " + url)
        req = urllib.request.Request(url, headers={"User-Agent": "civic-data-import/1.0 (public election information)"})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    if urlparse(r.geturl()).hostname != urlparse(url).hostname:
                        raise ValueError("unexpected redirect")
                    target.write_bytes(r.read(20 * 1024 * 1024))
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raise SystemExit("not found: " + url)
                time.sleep(3 + attempt * 3)
            except (OSError, ValueError):
                time.sleep(3 + attempt * 3)
        else:
            raise SystemExit("download failed: " + url)
        time.sleep(0.6)
    raw = target.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def roster():
    groups = [g for f in ("published-roster", "national-roster-supplement") for g in json.loads((ROOT / "data" / (f + ".json")).read_text())["districts"]]
    return {(g["county"], g["office"], g.get("number") if g["office"] == "council" else None): g for g in groups}


def parse_gazette(raw, page_url):
    soup = BeautifulSoup(raw, "html.parser")
    cards = []
    for a in soup.select("[data-candidate]"):
        photo = a.select_one('img[src*="/candidate-photos/"]')
        emblem = a.select_one('img[src*="/party-emblems/"]')
        tokens = [t for t in (x.strip() for x in a.stripped_strings) if t]
        nums = [t for t in tokens if t.isdigit()]
        if not nums:
            continue
        number = int(nums[0])
        rest = tokens[tokens.index(nums[0]) + 1:]
        if not rest:
            continue
        href = a.get("href") or ""
        cards.append({
            "number": number, "name": rest[0], "party": rest[1] if len(rest) > 1 else None,
            "photo": urljoin(page_url, photo["src"]) if photo else None,
            "emblem": urljoin(page_url, emblem["src"]) if emblem else None,
            "page": urljoin(page_url, href) if href else None,
        })
    uniq = {}
    for c in cards:
        uniq.setdefault(c["number"], c)
    return list(uniq.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    counties = json.loads((ROOT / "data/election.json").read_text())["counties"]
    code_by_name = {norm(c["name"]): c["code"] for c in counties}
    groups = roster()
    files = []
    raw, h = fetch(CEC + "/json/dist/prvCityDept.json", a.cache, a.offline)
    files.append({"url": CEC + "/json/dist/prvCityDept.json", "sha256": h})
    prvs = json.loads(raw)["prvs"]
    if len(prvs) != 22:
        raise SystemExit("expected 22 counties")
    official, problems = {}, []
    for p in prvs:
        county = code_by_name[norm(p["prvName"])]
        for kind in ("C1", "T"):
            url = f"{CEC}/json/cand/{kind}/{p['prvCityCode']}.json"
            raw, h = fetch(url, a.cache, a.offline)
            files.append({"url": url, "sha256": h})
            data = json.loads(raw)[kind]
            races = [(None, data)] if kind == "C1" else [(int(x["areaCode"]), x["cands"]) for x in data]
            for number, cands in races:
                g = groups.get((county, "chief" if kind == "C1" else "council", number))
                if not g:
                    problems.append({"source": "cec", "county": county, "district": number, "reason": "no_roster_race"})
                    continue
                if kind == "T":
                    seats = next(x["numberElected"] for x in data if int(x["areaCode"]) == number)
                    if seats != g["seats"]:
                        problems.append({"source": "cec", "race": g["id"], "reason": "seat_mismatch", "cec": seats, "roster": g["seats"]})
                by_no = {c["number"]: c for c in g["candidates"]}
                if len(cands) != len(by_no) or {c["candNo"] for c in cands} != set(by_no):
                    problems.append({"source": "cec", "race": g["id"], "reason": "ballot_numbers_differ"})
                    continue
                bad = [c["candNo"] for c in cands if not same_person_name(by_no[c["candNo"]]["name"], c["name"])]
                if bad:
                    problems.append({"source": "cec", "race": g["id"], "reason": "name_mismatch", "numbers": bad})
                    continue
                for c in cands:
                    r = by_no[c["candNo"]]
                    birth = re.fullmatch(r"(\d{3})(\d{2})(\d{2})", c.get("birth") or "")
                    official[r["id"]] = {
                        "official_name": c["name"].strip() if norm(c["name"]) != norm(r["name"]) else None,
                        "party": party_norm(c.get("party")) or None,
                        "gender": c.get("gender") if c.get("gender") in ("男", "女") else None,
                        "birth_year": int(birth.group(1)) + 1911 if birth else None,
                        "home": (c.get("home") or "").strip() or None,
                        "cec_photo": c["img"] if (c.get("img") or "").startswith("/json/portrait/cand/") else None,
                    }
    # Gazette display photos and emblems
    raw, h = fetch(GAZ + "/sitemap.xml", a.cache, a.offline)
    pages = [u for u in re.findall(r"<loc>([^<]+)</loc>", raw.decode()) if "/districts/" in u and not u.rstrip("/").endswith("/compare")]
    if len(pages) != 243:
        raise SystemExit("expected 243 district pages, found %d" % len(pages))
    photos, emblems, gaz_files = {}, {}, []
    emblem_votes = {}
    for url in sorted(pages):
        name = unquote(url.rstrip("/").rsplit("/", 1)[1])
        m = re.fullmatch(r"(.+?[縣市])(?:第(.+)選舉區)?", name)
        county = code_by_name.get(norm(m.group(1))) if m else None
        number = zh_number(m.group(2)) if m and m.group(2) else None
        g = groups.get((county, "council" if number else "chief", number))
        if not g:
            problems.append({"source": "gazette", "page": name, "reason": "no_roster_race"})
            continue
        raw, h = fetch(url, a.cache, a.offline)
        gaz_files.append({"url": url, "sha256": h})
        cards = parse_gazette(raw, url)
        by_no = {c["number"]: c for c in g["candidates"]}
        if {c["number"] for c in cards} != set(by_no):
            problems.append({"source": "gazette", "race": g["id"], "reason": "ballot_numbers_differ"})
            continue
        bad = [c["number"] for c in cards if not same_person_name(by_no[c["number"]]["name"], c["name"])]
        if bad:
            problems.append({"source": "gazette", "race": g["id"], "reason": "name_mismatch", "numbers": bad})
            continue
        for c in cards:
            r = by_no[c["number"]]
            ph = urlparse(c["photo"] or "")
            if ph.hostname == "gazette2026.taiwangogo.tw" and re.fullmatch(r"/candidate-photos/[0-9a-f]{64}\.webp", ph.path or ""):
                photos[r["id"]] = {"photo": ph.path.rsplit("/", 1)[1][:-5], "page": c["page"]}
            em = urlparse(c["emblem"] or "")
            if c["party"] and em.hostname == "gazette2026.taiwangogo.tw" and re.fullmatch(r"/brand/party-emblems/[A-Za-z0-9._-]+\.webp", em.path or ""):
                emblem_votes.setdefault(party_norm(c["party"]), Counter())[em.path] += 1
    for party, votes in emblem_votes.items():
        if party != "無" and len(votes) == 1:
            emblems[party] = next(iter(votes))
        elif party != "無":
            problems.append({"source": "gazette", "party": party, "reason": "conflicting_emblems"})
    records = {}
    all_ids = [c["id"] for g in groups.values() for c in g["candidates"]]
    conflicts = []
    rows = {c["id"]: c for g in groups.values() for c in g["candidates"]}
    for cid in sorted(all_ids):
        o = official.get(cid)
        p = photos.get(cid)
        if not o and not p:
            continue
        rec = dict(o or {})
        if p:
            rec.update(p)
        records[cid] = rec
        if o and rows[cid].get("party") is not None and party_norm(rows[cid]["party"]) != o["party"]:
            conflicts.append({"id": cid, "roster": rows[cid]["party"], "cec": o["party"]})
    stats = {
        "candidates": len(all_ids), "official_matched": len(official), "photos": len(photos),
        "emblems": len(emblems), "party_conflicts_with_roster": len(conflicts),
        "official_party": dict(Counter(r["party"] for r in official.values()).most_common()),
    }
    out = {
        "version": VERSION,
        "retrieved_on": time.strftime("%Y-%m-%d"),
        "notice": "號次、姓名、推薦政黨、性別、出生年及出生地取自中選會115年選舉專區官方資料；網頁顯示照片為中選會公告登記照，經《2026 民間版選舉公報》轉為WebP，政黨標誌亦取自該站內政部登記圖檔。照片與標誌不在該站CC BY 4.0授權範圍，本站僅以連結顯示、未複製。每一選區號次與姓名須一對一相符才採用。",
        "sources": {
            "cec": {"base": CEC, "site": "https://info.cec.gov.tw/vote2026/", "files": files},
            "gazette": {"base": GAZ, "license": GAZ + "/data-sources/#license", "credit": "資料來源：台灣前進《2026 民間版選舉公報》gazette2026.taiwangogo.tw", "pages": len(gaz_files), "files_sha256": hashlib.sha256(json.dumps(gaz_files, sort_keys=True).encode()).hexdigest()},
        },
        "stats": stats, "problems": problems, "party_conflicts": conflicts,
        "emblems": dict(sorted(emblems.items())), "records": records,
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(json.dumps(stats, ensure_ascii=False))
    print("problems", len(problems), json.dumps(problems[:20], ensure_ascii=False))
    print("conflicts", json.dumps(conflicts[:20], ensure_ascii=False))


if __name__ == "__main__":
    main()
