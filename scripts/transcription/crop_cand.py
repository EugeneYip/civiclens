"""Render the bulletin area around one candidate (found by name in the text layer) for visual checks.
Usage: python3 -I scripts/transcription/crop_cand.py PDF_DIR CANDIDATE_ID OUT_PREFIX [DPI]"""
import json, re, subprocess, sys
from pathlib import Path
S = Path(sys.argv[1]); k = sys.argv[2]; out = sys.argv[3]
d = json.loads((Path(__file__).resolve().parents[2] / "data/reviewed-council-policies.json").read_text())
r = d["records"][k]; url, pg = r["source"].split("#page="); pg = int(pg)
key = next(x for x, m in d["source_files"].items() if m["url"] == url)
pdf = S / key
x = subprocess.run(["pdftotext", "-f", str(pg), "-l", str(pg), "-bbox", str(pdf), "-"], capture_output=True, text=True).stdout
pw, ph = map(float, re.search(r'<page width="([\d.]+)" height="([\d.]+)"', x).groups())
name = re.sub(r"\s", "", r["name"].split(" ")[0])
m = [w for w in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', x) if w.group(5) == name]
if not m:
    print("name not in text layer; page", pg, pw, ph, pdf); sys.exit(1)
x0, y0 = float(m[0].group(1)), float(m[0].group(2))
left = max(0, x0 - 20); top = max(0, y0 - 60); W = min(pw - left, pw / 2 + 40); H = min(ph - top, 620)
dpi = int(sys.argv[4]) if len(sys.argv) > 4 else 110; s = dpi / 72
subprocess.run(["pdftoppm", "-f", str(pg), "-l", str(pg), "-r", str(dpi), "-x", str(int(left * s)), "-y", str(int(top * s)), "-W", str(int(W * s)), "-H", str(int(H * s)), "-png", str(pdf), out], capture_output=True)
print("ok", pdf.name, pg, [i["summary"] for i in r["items"]])
