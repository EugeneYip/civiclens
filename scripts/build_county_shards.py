"""Split per-candidate data layers into one file per county (data/county/<code>.json).

The explorer loads only the selected county's shard instead of seven national files.
Full source files stay unchanged; each shard records the source version and SHA-256.
Run with --check in CI to fail when a shard is stale.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "county"
VERSION = "0.1.29"
LAYERS = {  # key in shard: (file, expected version, keys that are per-candidate maps)
    "enrichment": ("candidate-enrichment.json", "0.1.13", ("records", "photos")),
    "careers": ("candidate-careers.json", "0.1.13", ("records",)),
    "parties": ("candidate-parties.json", "0.1.14", ("records",)),
    "bulletin": ("bulletin-facts.json", "0.1.15", ("records",)),
    "details": ("bulletin-details.json", "0.1.16", ("records",)),
    "official": ("cec-official-2026.json", "0.1.26", ("records",)),
    "moi": ("moi-portrait-references.json", "0.1.21", ("records",)),
    "councilReviews": ("reviewed-council-policies.json", "0.1.27", ("records",)),
}


def load(name):
    raw = (DATA / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def build():
    groups = [g for f in ("published-roster.json", "national-roster-supplement.json") for g in load(f)[0]["districts"]]
    by_county = {}
    for g in groups:
        by_county.setdefault(g["county"], set()).update(c["id"] for c in g["candidates"])
    hold = set(load("bulletin-quarantine.json")[0]["ids"])
    sources, layers = {}, {}
    for key, (name, version, maps) in LAYERS.items():
        data, sha = load(name)
        if data.get("version") != version:
            raise SystemExit(f"{name}: expected version {version}, found {data.get('version')}")
        sources[key] = {"file": name, "version": version, "sha256": sha}
        layers[key] = (data, maps)
    audit, audit_sha = load("image-availability-audit.json")
    sources["audit"] = {"file": "image-availability-audit.json", "version": audit["version"], "sha256": audit_sha}
    official = layers["official"][0]
    shards = {}
    for code, ids in sorted(by_county.items()):
        shard = {"version": VERSION, "county": code, "sources": sources, "quarantine": sorted(ids & hold)}
        for key, (data, maps) in layers.items():
            part = {m: {k: v for k, v in data[m].items() if k in ids and not (key == "bulletin" and k in hold)} for m in maps}
            shard[key] = part
        shard["emblems"] = official["emblems"]
        shard["audit"] = {"checked_at": audit["checked_at"], "records": {k: v for k, v in audit["records"].items() if k.split(":", 1)[-1] in ids}}
        shards[code] = json.dumps(shard, ensure_ascii=False, separators=(",", ":")) + "\n"
    return shards


def main():
    shards = build()
    if "--check" in sys.argv:
        stale = [c for c, text in shards.items() if not (OUT / f"{c}.json").exists() or (OUT / f"{c}.json").read_text() != text]
        if stale or len(list(OUT.glob("*.json"))) != len(shards):
            raise SystemExit("county shards are stale: " + ", ".join(stale))
        return
    OUT.mkdir(exist_ok=True)
    for c, text in shards.items():
        (OUT / f"{c}.json").write_text(text)
    sizes = {c: len(t.encode()) for c, t in shards.items()}
    print(len(shards), "shards; largest", max(sizes.values()), "bytes; total", sum(sizes.values()))


if __name__ == "__main__":
    main()
