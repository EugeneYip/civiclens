"""Check that each displayed candidate photo is the CEC registration photo of that candidate.

For every record in data/cec-official-2026.json with a display photo, download the gazette WebP
(the image the site shows) and the CEC registration photo (official, not embeddable), convert
both to 24x32 greyscale and compute the normalized correlation.  A low score means the displayed
image is not the registration photo (e.g. a party emblem was published in its place); such photos
are listed in data/photo-identity-audit.json and excluded by scripts/import_cec_official.py.

Usage: python3 scripts/audit_photo_identity.py --cache DIR [--offline]
"""
import argparse
import io
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "photo-identity-audit.json"
VERSION = "0.1.36"
THRESHOLD = 0.9
GAZ = "https://gazette2026.taiwangogo.tw/candidate-photos/"
CEC = "https://info.cec.gov.tw/vote2026/static"


def fetch(url, dest, offline):
    if dest.exists():
        return dest.read_bytes()
    if offline:
        return None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "civic-data-audit/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read()
            dest.write_bytes(raw)
            time.sleep(0.12)
            return raw
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 2 * attempt)
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(2 + 2 * attempt)
    return None


def vector(raw):
    im = Image.open(io.BytesIO(raw))
    im.load()
    px = list(im.convert("L").resize((24, 32)).tobytes())
    mean = sum(px) / len(px)
    v = [p - mean for p in px]
    n = sum(x * x for x in v) ** 0.5 or 1
    return [x / n for x in v], im.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    records = json.loads((ROOT / "data" / "cec-official-2026.json").read_text())["records"]
    prior = json.loads(OUTPUT.read_text())["rejected"] if OUTPUT.exists() else {}
    checked, rejected, unreadable, scores = 0, {}, [], []
    for cid, r in sorted(records.items()):
        photo = r.get("photo") or (prior.get(cid) or {}).get("photo")
        if not photo or not r.get("cec_photo"):
            continue
        g = fetch(GAZ + photo + ".webp", a.cache / f"{cid}.webp", a.offline)
        c = fetch(CEC + r["cec_photo"], a.cache / f"{cid}.cec.jpg", a.offline)
        try:
            (gv, gsize), (cv, _) = vector(g), vector(c)
        except Exception:
            unreadable.append(cid)
            continue
        checked += 1
        score = round(sum(x * y for x, y in zip(gv, cv)), 4)
        scores.append(score)
        if score < THRESHOLD:
            rejected[cid] = {"photo": photo, "similarity": score, "reason": "顯示圖檔與中選會登記照不符（相似度低於門檻）"}
    out = {
        "version": VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "將顯示用WebP與中選會登記照縮為24×32灰階後計算正規化相關係數；低於門檻者不採用。僅檢查是否為同一張登記照，不判讀人像。",
        "threshold": THRESHOLD,
        "stats": {"checked": checked, "rejected": len(rejected), "unreadable": len(unreadable),
                  "min_accepted": min((s for s in scores if s >= THRESHOLD), default=None)},
        "unreadable": unreadable,
        "rejected": rejected,
    }
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out["stats"], ensure_ascii=False), list(rejected))


if __name__ == "__main__":
    main()
