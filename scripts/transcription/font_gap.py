"""Hidden-font audit: list text that pdfium extracts but poppler (pdftotext) misses on each bulletin
page and that no transcription covers. Poppler renders some CID fonts blank, so a transcriber
working only from poppler images can silently skip lines; this check caught none missing in 2026
but must be run on every batch.

Usage: python3 -I scripts/transcription/font_gap.py PDF_DIR REVIEW_DIR [ID_PREFIX ...]
PDF_DIR holds the downloaded bulletins (keys as in data/reviewed-council-policies.json
source_files); REVIEW_DIR holds council_full_*.json transcriptions. Requires pypdfium2 and poppler.
"""
import json, re, subprocess, sys
from pathlib import Path
import pypdfium2 as pdfium
REPO = Path(__file__).resolve().parents[2]; PDFS = Path(sys.argv[1]); REVIEW = Path(sys.argv[2])
d = json.loads((REPO / "data/reviewed-council-policies.json").read_text())
recs = d["records"]; url2key = {m["url"]: k for k, m in d["source_files"].items()}
full = {}
for f in sorted(REVIEW.glob("council_full_*.json")):
    for k, v in json.loads(f.read_text())["records"].items(): full[k] = v
prefixes = sys.argv[3:] or None
def cjk(s): return re.sub(r"[^一-鿿]", "", s)
BOIL = re.compile(r"號次|學歷|經歷|基本資料|推薦之政黨|具結|聲明確|indd|出生|性別|大陸地區|中華民國以外|護照|戶籍|居民身分|投票|投開票|選舉人|選舉公報|選舉區|第\d+屆|罰|不服制止|開票|圈選|選舉罷免法|選舉類別|行政區|原住民 編號|所屬|里 全里|號 .*里")
pages = {}
for k, r in recs.items():
    if prefixes and not any(k.startswith(p) for p in prefixes): continue
    url, pg = r["source"].split("#page="); key = url2key[url]
    pdf = PDFS / key
    pg = int((full.get(k) or {}).get("page") or pg)
    pages.setdefault((str(pdf), pg), []).append(k)
report = {}
for (pdf, pg), ks in sorted(pages.items()):
    try:
        doc = pdfium.PdfDocument(pdf); tp = doc[pg - 1].get_textpage(); ptxt = tp.get_text_range(); doc.close()
    except Exception as e:
        print("ERR", pdf, pg, e); continue
    pop = cjk(subprocess.run(["pdftotext", "-f", str(pg), "-l", str(pg), pdf, "-"], capture_output=True, text=True).stdout)
    covered = ""
    for k in ks:
        x = full.get(k) or {}
        covered += cjk(" ".join(i["text"] for s in x.get("sections", []) for i in s["items"]) + " ".join((s.get("heading") or "") + (s.get("group") or "") for s in x.get("sections", [])) + (x.get("headline") or ""))
        r = recs[k]; covered += cjk(" ".join(r.get("education", []) + r.get("experience", [])) + r["name"])
    for line in re.split(r"[\r\n]+", ptxt):
        c = cjk(line)
        if len(c) < 6 or BOIL.search(line): continue
        sh = [c[i:i+4] for i in range(len(c) - 3)]
        in_pop = sum(s in pop for s in sh) / len(sh)
        in_cov = sum(s in covered for s in sh) / len(sh)
        if in_pop < 0.5 and in_cov < 0.5:
            report.setdefault(f"{Path(pdf).name} p{pg}", {"candidates": ks, "lines": []})["lines"].append(line.strip()[:120])
json.dump(report, open(S.parent / "audit/font_gap_report.json", "w"), ensure_ascii=False, indent=1)
tot = sum(len(v["lines"]) for v in report.values())
print("pages with uncovered pdfium-only text:", len(report), "lines:", tot)
for p, v in list(report.items())[:40]:
    print("==", p, v["candidates"][:3], "...", len(v["lines"]))
    for l in v["lines"][:4]: print("    ", l)
