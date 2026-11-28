"""Build data/taiwan-counties-map.json (simplified SVG paths for the 22 counties) from the
taiwan-atlas TopoJSON (pre-built from the Ministry of the Interior county boundaries).

Usage: python3 -I scripts/build_map_geometry.py COUNTIES_10T_JSON
Source file: https://cdn.jsdelivr.net/npm/taiwan-atlas@2021.9.20/counties-10t.json (MIT),
itself derived from 內政部國土測繪中心「直轄市、縣市界線(TWD97經緯度)」 (data.gov.tw dataset 7442).
Kinmen and Lienchiang are drawn in insets; everything else keeps its true position.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = "https://cdn.jsdelivr.net/npm/taiwan-atlas@2021.9.20/counties-10t.json"
W = 360.0  # viewBox width; height follows from the projection
LAT0 = 23.7
KX = math.cos(math.radians(LAT0))
MAIN = (119.28, 21.88, 122.12, 25.36)  # lon/lat box for Taiwan, Penghu and nearby islands
INSETS = {"09007": (119.85, 25.92, 120.55, 26.41), "09020": (118.18, 24.36, 118.52, 24.53)}


def decode(topo):
    sx, sy = topo["transform"]["scale"]; tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in arc:
            x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx):
        out = []
        for i in idx:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out
    return ring


def simplify(pts, tol):
    if len(pts) < 4:
        return pts
    if pts[0] == pts[-1]:  # closed ring: split at the farthest point so the baseline is not degenerate
        x0, y0 = pts[0]; k = max(range(len(pts)), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - y0) ** 2)
        if 0 < k < len(pts) - 1:
            return simplify(pts[:k + 1], tol)[:-1] + simplify(pts[k:], tol)
    keep = [False] * len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop(); (x1, y1), (x2, y2) = pts[a], pts[b]; best, bi = 0, None
        dx, dy = x2 - x1, y2 - y1; den = math.hypot(dx, dy) or 1e-12
        for i in range(a + 1, b):
            x0, y0 = pts[i]; d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / den
            if d > best:
                best, bi = d, i
        if bi is not None and best > tol:
            keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def main(path):
    raw = Path(path).read_bytes(); topo = json.loads(raw); ring = decode(topo)
    lon0, lat0, lon1, lat1 = MAIN
    s = W / ((lon1 - lon0) * KX); H = (lat1 - lat0) * s
    proj = lambda lon, lat: ((lon - lon0) * KX * s, (lat1 - lat) * s)
    inset_boxes = {"09007": (4, 4, 112, 92), "09020": (4, 104, 112, 46)}  # x, y, w, h in viewBox units
    counties = {}
    for g in topo["objects"]["counties"]["geometries"]:
        p = g["properties"]; code = p["COUNTYCODE"]; name = p["COUNTYNAME"].replace("台", "臺")
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        rings = [ring(poly[0]) for poly in polys]
        holes = [ring(h) for poly in polys for h in poly[1:]]  # e.g. 新北市 around 臺北市, 嘉義縣 around 嘉義市
        if code in INSETS:
            a0, b0, a1, b1 = INSETS[code]; bx, by, bw, bh = inset_boxes[code]
            k = min(bw / ((a1 - a0) * KX), bh / (b1 - b0)) * 0.9
            ox = bx + (bw - (a1 - a0) * KX * k) / 2; oy = by + (bh - (b1 - b0) * k) / 2
            f = lambda lon, lat: (ox + (lon - a0) * KX * k, oy + (b1 - lat) * k)
        else:
            f = proj
        pr = [[f(x, y) for x, y in r] for r in rings]
        big = max(area(r) for r in pr)
        parts = []
        for r in pr:
            if area(r) < max(0.6, big * 0.002) and area(r) != big:
                continue  # drop specks; keep every county's largest piece
            r = simplify(r, 0.35)
            if len(r) >= 3 and sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1])) < 0:
                r = r[::-1]  # consistent winding
            if len(r) >= 3:
                parts.append("M" + "L".join("%.1f %.1f" % pt for pt in r) + "Z")
        for h in holes:  # drawn with fill-rule evenodd, so holes stay empty and the enclave shows
            h = simplify([f(x, y) for x, y in h], 0.35)
            if len(h) >= 3:
                parts.append("M" + "L".join("%.1f %.1f" % pt for pt in h) + "Z")
        cx = sum(x for x, _ in max(pr, key=area)) / len(max(pr, key=area))
        cy = sum(y for _, y in max(pr, key=area)) / len(max(pr, key=area))
        counties[code] = {"name": name, "d": "".join(parts), "c": [round(cx, 1), round(cy, 1)], "_a": big}
    counties = {k: {x: y for x, y in v.items() if x != "_a"} for k, v in sorted(counties.items(), key=lambda kv: -kv[1]["_a"])}  # small (enclosed) counties last
    if len(counties) != 22:
        raise SystemExit("expected 22 counties, got %d" % len(counties))
    out = {"version": "0.1.82", "source": SRC, "sha256": hashlib.sha256(raw).hexdigest(),
           "basis": "內政部國土測繪中心「直轄市、縣市界線(TWD97經緯度)」，經 taiwan-atlas 轉為 TopoJSON；本站簡化繪製，金門縣、連江縣以插圖表示。",
           "viewBox": "0 0 %d %d" % (round(W), round(H)),
           "insets": [{"code": c, "box": list(b)} for c, b in inset_boxes.items()], "counties": counties}
    (ROOT / "data/taiwan-counties-map.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    print("viewBox", out["viewBox"], "bytes", len(json.dumps(out, ensure_ascii=False)))


if __name__ == "__main__":
    main(sys.argv[1])
