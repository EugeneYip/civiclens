"""Merge reviewed council platform transcriptions into data/council-bulletin-policies.json, then
rebuild the county shards. Reference implementation used for the 2026-11-28 election.

Usage: python3 -I scripts/transcription/merge_council_full.py REVIEW_DIR TAG [TAG ...]
REVIEW_DIR holds council_full_<TAG>.json files written by the transcription agents (see
docs/playbook/transcription-prompt.md). Those raw files are NOT committed: they still contain contact
details and third-party remarks that the published data deliberately omits.

The rule tables below record the editorial decisions taken after checking each case against the
printed bulletin (ids are this site's candidate ids). Guards abort the merge on ID-like strings,
phone numbers, street addresses (unless reviewed as public facilities) and unreadable marks.
"""
import json, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]; REVIEW = Path(sys.argv[1]); TAGS = sys.argv[2:]
TOPICS = {"交通","居住與都市","教育與青年","育兒與社福","醫療與健康","經濟與就業","環境與能源","文化與觀光","治理與安全"}
FW = str.maketrans("０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
# Sections that are self-introductions or closing remarks, not policies (checked against the bulletin).
INTRO_CHIEF_UNUSED = {"02-chief-3": [0], "03-chief-3": [10], "04-chief-3": [5], "01-chief-4": [0], "04-chief-1": [0], "09-chief-1": [0], "09-chief-2": [0], "09-chief-4": [0], "10-chief-1": [0], "13-chief-2": [0], "05-chief-5": [0], "06-chief-2": [0], "16-chief-1": [0], "16-chief-2": [0], "17-chief-5": [0], "15-chief-4": [0], "21-chief-5": [0, 1, 3], "21-chief-6": [1], "21-chief-1": [0, 4], "20-chief-4": [0]}
INTRO = {"01-council-6-2": [0], "01-council-6-8": [0], "01-council-5-5": [10], "01-council-6-10": [5], "01-council-1-7": [0, 7], "01-council-2-6": [0, 1, 3], "01-council-2-4": [0], "01-council-2-8": [1], "01-council-2-7": [0, 4], "02-council-9-1": [4], "02-council-9-2": [6], "02-council-9-5": [0, 6], "02-council-11-1": [0], "02-council-11-8": [0], "02-council-11-9": [0, 5], "02-council-12-2": [6], "02-council-12-6": [0], "02-council-13-1": [5], "02-council-13-6": [0], "02-council-1-2": [5], "02-council-1-5": [5], "02-council-2-3": [0], "02-council-2-5": [0], "02-council-3-3": [1], "02-council-3-4": [1], "02-council-3-5": [0], "02-council-3-6": [0], "02-council-3-9": [0, 7], "02-council-4-6": [0], "02-council-4-11": [0], "02-council-5-3": [0, 6], "02-council-5-10": [0], "02-council-6-3": [0], "02-council-6-4": [0], "02-council-6-5": [0], "02-council-8-5": [4], "03-council-1-4": [0], "03-council-5-2": [0], "03-council-5-3": [0], "03-council-5-10": [0], "03-council-11-1": [0], "03-council-11-2": [0], "03-council-11-4": [0], "03-council-11-8": [1], "03-council-12-4": [0, 9], "03-council-12-7": [0], "03-council-13-2": [5], "03-council-13-9": [0], "03-council-17-2": [5], "03-council-17-4": [0], "03-council-7-5": [0], "03-council-8-3": [0], "03-council-8-4": [1], "03-council-8-6": [19], "03-council-9-2": [2], "03-council-9-4": [0], "03-council-10-2": [0, 2], "03-council-10-3": [0], "04-council-1-3": [0, 2, 3], "04-council-1-7": [9], "04-council-2-1": [0], "04-council-2-5": [6], "04-council-5-5": [0], "04-council-9-2": [0, 3], "04-council-9-3": [0], "04-council-9-4": [6], "04-council-9-6": [6], "04-council-10-1": [0], "04-council-10-3": [0], "04-council-10-4": [0], "04-council-11-9": [1], "04-council-6-1": [0], "04-council-7-8": [0], "04-council-8-5": [5], "04-council-8-6": [0, 2], "04-council-8-7": [9], "04-council-8-10": [0], "05-council-3-5": [2], "05-council-4-2": [0], "05-council-4-4": [0, 2], "05-council-4-6": [9], "05-council-4-9": [0], "05-council-6-1": [1], "05-council-7-3": [2], "05-council-8-6": [0], "05-council-8-8": [5], "05-council-9-2": [0], "05-council-9-7": [0], "05-council-10-2": [0], "05-council-10-3": [0], "05-council-10-13": [5], "05-council-15-1": [0], "06-council-1-5": [0, 6], "06-council-2-2": [6], "06-council-2-5": [7], "06-council-3-5": [7], "06-council-4-5": [0], "06-council-6-1": [0], "06-council-6-2": [0], "06-council-7-2": [1], "06-council-7-6": [0], "06-council-7-9": [0], "06-council-7-16": [0], "06-council-8-5": [0], "06-council-8-9": [0, 13], "06-council-9-1": [4], "06-council-9-3": [0, 3], "06-council-9-7": [0], "06-council-12-2": [0], "06-council-13-1": [1], "06-council-14-1": [0, 1, 6], "06-council-14-5": [0], "07-council-1-3": [0], "07-council-2-9": [6], "07-council-3-9": [0], "08-council-1-3": [6], "08-council-1-4": [0], "08-council-1-6": [0, 3], "08-council-1-13": [5], "08-council-2-3": [0], "08-council-3-4": [0, 2], "08-council-3-6": [0], "07-council-4-2": [0], "07-council-9-3": [6], "07-council-13-1": [0], "07-council-13-4": [0], "08-council-5-5": [0, 1], "08-council-5-7": [5], "08-council-5-11": [0], "09-council-4-12": [0], "09-council-6-2": [0, 2], "09-council-6-6": [0], "09-council-1-5": [0, 2], "09-council-1-8": [4], "09-council-2-5": [6], "09-council-2-6": [1], "09-council-7-4": [0], "09-council-10-1": [0], "09-council-10-2": [34], "09-council-10-3": [0], "10-council-1-2": [1], "10-council-1-6": [0], "10-council-1-11": [0, 2], "10-council-1-13": [0, 6], "10-council-2-1": [0], "10-council-2-8": [0], "10-council-2-11": [0, 5], "10-council-3-4": [0], "10-council-5-7": [0], "10-council-5-8": [0], "11-council-2-4": [6], "11-council-4-2": [0], "11-council-4-7": [1], "11-council-5-9": [0, 6], "11-council-6-4": [7], "12-council-1-9": [1], "12-council-2-4": [0], "12-council-2-9": [0, 9], "12-council-2-13": [0], "12-council-2-14": [0], "12-council-3-1": [0], "12-council-4-3": [6], "12-council-5-1": [6], "13-council-6-1": [8], "13-council-12-3": [0, 2], "13-council-15-1": [0], "13-council-16-2": [0, 7], "13-council-4-2": [0, 1, 3], "13-council-4-9": [1], "13-council-1-12": [0, 2], "13-council-1-15": [0, 2], "13-council-2-3": [0], "13-council-2-7": [1], "13-council-2-8": [6], "13-council-2-11": [0, 2], "14-council-1-1": [1], "14-council-1-3": [0, 2], "14-council-1-8": [1], "14-council-1-14": [0], "14-council-7-4": [0, 2], "14-council-7-6": [0], "14-council-12-1": [0], "14-council-16-3": [1], "15-council-1-12": [0, 7], "15-council-1-15": [0, 5, 7], "15-council-3-9": [0, 6], "15-council-3-10": [0, 2], "15-council-4-2": [0, 6], "15-council-4-3": [1], "15-council-6-1": [0], "15-council-6-2": [0], "15-council-6-4": [0], "15-council-8-2": [0, 1], "15-council-10-2": [8], "17-council-1-7": [1], "17-council-1-17": [0], "16-council-1-3": [0], "16-council-1-4": [1], "16-council-1-8": [0, 2], "16-council-1-10": [0], "16-council-1-13": [0, 6], "16-council-1-15": [0, 8], "16-council-2-1": [1], "16-council-2-3": [0], "16-council-3-5": [0], "16-council-4-2": [4], "16-council-5-1": [5], "16-council-6-8": [0], "16-council-7-3": [0], "16-council-9-1": [7], "16-council-9-4": [1], "16-council-9-5": [0, 7], "16-council-11-1": [0, 7], "16-council-12-2": [0], "18-council-1-1": [0], "18-council-1-2": [0], "18-council-2-3": [5], "18-council-2-5": [6], "18-council-2-7": [0], "18-council-2-8": [0], "18-council-4-7": [5], "18-council-5-1": [0, 2], "18-council-5-9": [0, 2], "18-council-5-10": [0], "18-council-6-3": [1], "18-council-6-4": [0], "18-council-6-5": [0, 10], "18-council-9-1": [0], "21-council-1-6": [0], "21-council-1-12": [0, 7], "21-council-2-3": [1], "21-council-2-8": [0], "21-council-2-10": [1], "21-council-3-1": [0, 2], "22-council-1-4": [0], "22-council-3-2": [0], "22-council-4-1": [0, 6], "19-council-1-1": [6], "19-council-1-7": [3], "19-council-1-8": [7], "19-council-1-10": [0], "19-council-1-11": [0], "19-council-1-13": [0], "19-council-1-18": [0], "19-council-2-5": [1], "19-council-4-1": [3], "19-council-4-2": [0, 4], "19-council-4-8": [1], "19-council-5-7": [0, 2], "19-council-5-8": [0], "19-council-6-1": [0], "19-council-7-3": [1], "20-council-1-3": [0, 3], "20-council-1-7": [0], "20-council-1-10": [3], "20-council-1-12": [0], "20-council-2-10": [0], "20-council-2-11": [0], "20-council-2-16": [1], "19-council-4-7": [2]}
# Not published verbatim (low-resolution bulletin images; most text uncertain or incomplete) -> keep the summary.
REDACT_PATTERNS = [(re.compile(r"手機09\d{8}"), "手機（號碼略）")]  # 2026: one candidate printed a mobile number inside a platform line
RECORD = {"04-council-1-8": [0], "04-council-2-5": [5]}
NORMPUNCT = {"15-council-1-15", "04-council-1-7", "04-council-2-1", "04-council-5-4", "04-council-5-7"}
PUNCT = {",": "，", ";": "；", ":": "：", "!": "！", "?": "？"}
RECORDONLY = {"04-council-7-7", "06-council-11-1", "10-council-1-9"}
ADDRESS_OK = {"05-council-4-4", "04-council-3-1", "19-council-4-3"}  # 左楠路2號 is the CPC refinery site (public facility), not a private address
HEADLINE_NULL = {"05-council-6-3"}  # 2x2 slogan with ambiguous reading order
DROPSEC = {"10-council-1-16": [13], "17-council-2-4": [6], "18-council-2-8": [6], "05-council-8-8": [5]}  # service-office contact addresses, not platform text
EXCLUDE = {"20-council-2-12", "13-council-1-14", "11-council-6-6", "11-council-1-4", "11-council-1-6", "09-council-3-1", "09-council-4-2", "07-council-3-11", "04-council-10-6", "04-council-1-1", "03-council-8-1", "01-council-1-1", "01-council-1-15", "01-council-2-3", "01-council-3-10", "01-council-3-12", "01-council-4-12", "01-council-5-12", "01-council-6-16"}
# Published with a low-resolution warning (only isolated characters uncertain; noted by the transcriber).
LOWRES = {"10-council-1-6", "09-council-8-5", "09-council-10-2", "09-council-10-3", "09-council-1-6", "09-council-1-14", "07-council-9-6", "03-council-8-12", "01-council-1-2", "01-council-1-11", "01-council-1-13", "01-council-1-14", "01-council-1-16", "01-council-1-18", "01-council-1-19", "01-council-1-20", "01-council-2-2", "01-council-2-4", "01-council-2-10", "01-council-3-2", "01-council-3-4", "01-council-3-5", "01-council-4-4", "01-council-5-5", "01-council-5-6", "01-council-6-7", "01-council-6-13", "01-council-8-1"}
pilot = json.loads((REPO / "data/reviewed-council-policies.json").read_text())["records"]
out_path = REPO / "data/council-bulletin-policies.json"
data = json.loads(out_path.read_text())
for tag in TAGS:
    recs = json.loads((REVIEW / f"council_full_{tag}.json").read_text())["records"]
    for k, x in recs.items():
        if k in EXCLUDE:
            data["records"].pop(k, None); continue
        p = pilot[k]
        if (x["name"], x["number"]) != (p["name"], p["number"]): raise SystemExit(f"{k}: name/number")
        secs = []
        for si, sec in enumerate(x["sections"]):
            if si in DROPSEC.get(k, []): continue
            if si in INTRO.get(k, []): sec["kind"] = "intro"
            if si in RECORD.get(k, []): sec["kind"] = "record"
            if sec.get("kind") not in ("policy", "record", "intro"): raise SystemExit(f"{k}: kind {sec.get('kind')}")
            items = []
            for it in sec["items"]:
                t = re.sub(r"\s+", " ", it["text"].translate(FW)).strip()
                tp = [z for z in it.get("topics") or []]
                if not t or not tp or len(tp) > 2 or any(z not in TOPICS for z in tp): raise SystemExit(f"{k}: bad item {it}")
                if re.search(r"[A-Z][12]\d{8}", t): raise SystemExit(f"{k}: ID-like string")
                for pat, rep in REDACT_PATTERNS: t = pat.sub(rep, t)
                if k in NORMPUNCT: t = re.sub(r"(?<=[\u4e00-\u9fff）」』])\s*([,;:!?])\s*", lambda m: PUNCT[m.group(1)], t)
                if re.search(r"09\d{2}-?\d{3}-?\d{3}|0\d-?\d{7,8}", t) or (k not in ADDRESS_OK and re.search(r"[路街巷弄村里鄰]\d+(?:之\d+)?號", t)): raise SystemExit(f"{k}: phone/address in {t}")
                if "□" in t: raise SystemExit(f"{k}: unreadable mark in {t}")
                items.append({"text": t, "topics": tp})
            if items:
                secs.append({"heading": (sec.get("heading") or None), "group": (sec.get("group") or None), "kind": sec["kind"], "items": items})
        if not any(s["kind"] in ("policy", "intro") for s in secs) and k not in RECORDONLY: raise SystemExit(f"{k}: no policy items")
        src = p["source"].split("#")[0] + "#page=" + str(int(x.get("page") or p["source"].split("#page=")[1]))
        data["records"][k] = {"name": p["name"], "number": p["number"], "source": src, "headline": (None if k in HEADLINE_NULL else x.get("headline") or None), "sections": secs}
        if k in LOWRES: data["records"][k]["source_quality"] = "low_resolution"
data["records"] = dict(sorted(data["records"].items(), key=lambda kv: (kv[0].split("-")[0], int(kv[0].split("-")[2]), int(kv[0].split("-")[3]))))
out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
n = sum(len(s["items"]) for r in data["records"].values() for s in r["sections"])
print(len(data["records"]), "candidates,", n, "items")

import subprocess
subprocess.run(["python3", str(REPO / "scripts/build_county_shards.py")], check=True)
