"""Build data/council-maps/<county code>.json: council electoral districts drawn from township
(and, where a township is split, village) boundaries, for the results page.

Usage: python3 -I scripts/build_council_maps.py TOWNS_10T_JSON VILLAGES_10T_JSON
Sources: taiwan-atlas@2021.9.20 towns-10t.json / villages-10t.json (MIT), pre-built from the
Ministry of the Interior boundaries; district composition from data/council-districts.json
(CEC announcements). Districts are unions of whole townships, except 新竹縣 1–2 (竹北市) and
新竹市 1–5, which are built from villages. Indigenous districts cover the whole county and are
listed, not drawn. Distant outlying islands (e.g. 東沙、南沙、烏坵、釣魚臺) are omitted and named.
Arcs are simplified once, so shared borders stay identical on both sides.
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/council-maps"
W = 340.0
VILLAGE_COUNTIES = {"新竹縣", "新竹市"}


def norm(s):
    return s.replace("台", "臺")


def decode_arcs(topo):
    sx, sy = topo["transform"]["scale"]; tx, ty = topo["transform"]["translate"]; arcs = []
    for arc in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in arc:
            x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    return arcs


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True; st = [(0, len(pts) - 1)]
    while st:
        a, b = st.pop(); (x1, y1), (x2, y2) = pts[a], pts[b]; dx, dy = x2 - x1, y2 - y1; den = math.hypot(dx, dy)
        best, bi = 0, None
        for i in range(a + 1, b):
            x0, y0 = pts[i]
            d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / den if den else math.hypot(x0 - x1, y0 - y1)
            if d > best:
                best, bi = d, i
        if bi is not None and best > tol:
            keep[bi] = True; st += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def area(r):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]))) / 2


def scope_parts(scope):
    """'竹北市尚義里、崇義里、湖口鄉' -> [('竹北市','尚義里'),('竹北市','崇義里'),('湖口鄉',None)]."""
    out, town = [], None
    for p in re.split(r"[、，,]", scope):
        p = p.strip()
        m = re.fullmatch(r"([一-鿿]{1,4}?[鄉鎮市區])([一-鿿]{1,5}[村里])", p)
        if m:
            town = m.group(1); out.append((town, m.group(2)))
        elif re.fullmatch(r"[一-鿿]{1,5}[村里]", p):
            out.append((town or "*", p))  # 新竹市 lists villages without the township name
        elif re.fullmatch(r"[一-鿿]{1,4}[鄉鎮市區]", p):
            town = p; out.append((p, None))
        else:
            raise ValueError("unparsed scope part %r" % p)
    return out


def main(towns_path, villages_path):
    towns, vills = json.loads(Path(towns_path).read_text()), json.loads(Path(villages_path).read_text())
    T = {"topo": towns, "arcs": decode_arcs(towns), "geoms": towns["objects"]["towns"]["geometries"]}
    V = {"topo": vills, "arcs": decode_arcs(vills), "geoms": vills["objects"]["villages"]["geometries"]}
    cd = json.loads((ROOT / "data/council-districts.json").read_text())
    OUT.mkdir(exist_ok=True); report = []
    for county in cd["counties"]:
        name = county["name"]; src = V if name in VILLAGE_COUNTIES else T
        feats = [g for g in src["geoms"] if norm(g["properties"]["COUNTYNAME"]) == name]
        if not feats:
            raise SystemExit("no features for " + name)
        cec = feats[0]["properties"]["COUNTYCODE"]
        # district assignment
        whole, part, indig = {}, {}, []
        for d in county["districts"]:
            if "原住民" in d["scope"]:
                indig.append({"number": d["number"], "scope": d["scope"], "seats": d["seats"]}); continue
            for town, vil in scope_parts(d["scope"]):
                (part if vil else whole)[(town, vil) if vil else town] = d["number"]
        names = defaultdict(set)
        for g in feats:
            if g["properties"].get("VILLNAME"):
                names[g["properties"]["VILLNAME"]].add(norm(g["properties"]["TOWNNAME"]))
        for (town, vil) in [k for k in part if k[0] == "*"]:
            if len(names.get(vil, ())) != 1:
                raise SystemExit("%s: village %s is missing or ambiguous in the boundary data" % (name, vil))
            part[(next(iter(names[vil])), vil)] = part.pop((town, vil))
        for k in list(part):
            if k[1] not in names or k[0] not in names[k[1]]:
                raise SystemExit("%s: village %s%s not found in the boundary data" % (name, k[0], k[1]))
        assign = {}
        for i, g in enumerate(feats):
            p = g["properties"]; town = norm(p["TOWNNAME"]); vil = p.get("VILLNAME")
            num = part.get((town, vil)) if vil and (town, vil) in part else whole.get(town)
            if num is None and vil:  # village-level county: whole township listed by name
                num = whole.get(town)
            if num is None:
                raise SystemExit("%s: feature %s %s has no district" % (name, town, vil or ""))
            assign[i] = num
        # rings per feature (list of polygons -> outer ring arc lists)
        polys = []  # (feature index, [arc indices])
        for i, g in enumerate(feats):
            ps = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
            for poly in ps:
                polys.append((i, poly[0]))
        arcs = src["arcs"]
        ring_pts = lambda idx: [pt for k, a in enumerate(idx) for pt in ((arcs[a] if a >= 0 else arcs[~a][::-1])[(1 if k else 0):])]
        # outlying-island filter on raw lon/lat
        raw = [(i, ring_pts(r)) for i, r in polys]
        big = max(area(p) for _, p in raw)
        core = [p for _, p in raw if area(p) >= big * 0.05]
        xs = [x for p in core for x, _ in p]; ys = [y for p in core for _, y in p]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys); ex, ey = (x1 - x0) * 0.6 + 0.02, (y1 - y0) * 0.6 + 0.02
        keep, omitted = [], set()
        for (i, r), (_, pts) in zip(polys, raw):
            cx = sum(x for x, _ in pts) / len(pts); cy = sum(y for _, y in pts) / len(pts)
            if x0 - ex <= cx <= x1 + ex and y0 - ey <= cy <= y1 + ey:
                keep.append((i, r))
            else:
                omitted.add(norm(feats[i]["properties"]["TOWNNAME"]))
        omitted -= {norm(feats[i]["properties"]["TOWNNAME"]) for i, _ in keep}  # only whole townships left out
        # projection fitted to kept geometry
        kpts = [pt for _, r in keep for pt in ring_pts(r)]
        lon0, lon1 = min(x for x, _ in kpts), max(x for x, _ in kpts); lat0, lat1 = min(y for _, y in kpts), max(y for _, y in kpts)
        kx = math.cos(math.radians((lat0 + lat1) / 2)); s = W / ((lon1 - lon0) * kx); H = (lat1 - lat0) * s
        if H > W * 1.45:  # tall counties: cap height, narrower width
            s *= (W * 1.45) / H; H = (lat1 - lat0) * s
        pw = (lon1 - lon0) * kx * s; ox = (W - pw) / 2
        proj = lambda p: (round(ox + (p[0] - lon0) * kx * s, 1), round((lat1 - p[1]) * s, 1))
        used = sorted({abs(a) if a >= 0 else ~a for _, r in keep for a in r})
        tol = 0.45 if name not in VILLAGE_COUNTIES else 0.3
        simp = {a: dp([proj(p) for p in arcs[a]], tol) for a in used}
        # which districts / features use each arc
        arc_d, arc_f = defaultdict(set), defaultdict(set)
        for i, r in keep:
            for a in r:
                k = a if a >= 0 else ~a; arc_d[k].add(assign[i]); arc_f[k].add(i)
        def ring_d(idx):
            pts = []
            for k, a in enumerate(idx):
                seg = simp[a] if a >= 0 else simp[~a][::-1]
                pts.extend(seg if k == 0 else seg[1:])
            return pts
        dpaths, labels = defaultdict(list), {}
        best = {}
        for i, r in keep:
            pts = ring_d(r)
            if len(pts) < 3:
                continue
            if sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) < 0:
                pts = pts[::-1]  # same winding for every ring, so enclaves stay filled under the nonzero rule
            num = assign[i]; dpaths[num].append("M" + "L".join("%g %g" % p for p in pts) + "Z")
            a = area(pts)
            if a > best.get(num, (0,))[0]:
                best[num] = (a, (round(sum(x for x, _ in pts) / len(pts), 1), round(sum(y for _, y in pts) / len(pts), 1)))
        border = [k for k in used if len(arc_d[k]) > 1 or len(arc_f[k]) == 1]
        inner = [k for k in used if len(arc_d[k]) == 1 and len(arc_f[k]) > 1]
        line = lambda ks: "".join("M" + "L".join("%g %g" % p for p in simp[k]) for k in ks if len(simp[k]) > 1)
        regular = [d["number"] for d in county["districts"] if "原住民" not in d["scope"]]
        missing = [n for n in regular if n not in dpaths]
        if missing:
            raise SystemExit("%s: districts without shapes %s" % (name, missing))
        # neutral base of whole townships, so land outside any village (e.g. an air base) is not a white hole
        base = []
        for g in T["geoms"]:
            if norm(g["properties"]["COUNTYNAME"]) != name:
                continue
            for poly in (g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]):
                pts = [pt for k, a in enumerate(poly[0]) for pt in ((T["arcs"][a] if a >= 0 else T["arcs"][~a][::-1])[(1 if k else 0):])]
                cx = sum(x for x, _ in pts) / len(pts); cy = sum(y for _, y in pts) / len(pts)
                if not (x0 - ex <= cx <= x1 + ex and y0 - ey <= cy <= y1 + ey):
                    continue
                q = dp([proj(pt) for pt in pts], tol)
                if len(q) >= 3:
                    base.append("M" + "L".join("%g %g" % pt for pt in q) + "Z")
        doc = {"version": "0.1.84", "county": name, "cec": cec, "viewBox": "0 0 %g %g" % (W, round(H, 1)),
               "base": "".join(base) if name in VILLAGE_COUNTIES else "",
               "districts": {str(n): {"d": "".join(dpaths[n]), "label": best[n][1]} for n in regular},
               "borders": line(border), "towns": line(inner), "indigenous": indig, "omitted": sorted(omitted),
               "basis": "內政部國土測繪中心鄉鎮市區及村里界線（經 taiwan-atlas 轉製）；選區組成依中選會公告。"}
        (OUT / ("%s.json" % cec)).write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
        report.append("%s %s districts=%d indigenous=%d omitted=%s bytes=%d" % (name, cec, len(regular), len(indig), ",".join(sorted(omitted)) or "-", (OUT / ("%s.json" % cec)).stat().st_size))
    index = {json.loads(f.read_text())["county"]: f.stem for f in sorted(OUT.glob("[0-9]*.json"))}
    if len(index) != 22:
        raise SystemExit("expected 22 county maps")
    (OUT / "index.json").write_text(json.dumps({"version": "0.1.84", "counties": index}, ensure_ascii=False) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
