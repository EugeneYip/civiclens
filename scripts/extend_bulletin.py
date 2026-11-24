"""Generate a conservative second-pass bulletin match and source-linked detail index."""
import argparse, collections, hashlib, json, re, sqlite3, tempfile, unicodedata, urllib.request
from pathlib import Path
from stage_bulletin import ROOT, URL, ORIGIN, MAX_BYTES, roster_index, official_url, stage, strings
from derive_bulletin import derive

def norm_name(s):
    # Formatting only: do not map different Han characters or drop any name components.
    return re.sub(r"[\s·・．‧.]", "", unicodedata.normalize("NFKC", s)).casefold()

def norm_district(s):
    s=unicodedata.normalize("NFKC",s).replace("台","臺")
    return re.sub(r"第0+(\d+)選舉區",r"第\1選舉區",re.sub(r"\s+","",s))

def norm_key(k):
    o,d,n,name=k
    return (o,norm_district(d),n,norm_name(name))

# A fixed vocabulary and explicit numeric units; no extracted prose or inferred promises.
MEASURES=("免費","減免","補助","津貼","貸款","增設","新建","改善","延長","擴大","調高","降低","增加","減少","整建","設置","提供")
AMOUNT=re.compile(r"(?<![\d.])(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?\s*(?:億元|萬元|千元|百元|元|%|％|公里|公尺|公頃|個月|年|小時|分鐘|班次|席|戶|名|處|座|所|班)(?![\d])")
def policy_details(text, topics):
    out=[]
    for line in re.split(r"[。！？；\n]",unicodedata.normalize("NFKC",text)):
        if len(line)>160 or not line.strip(): continue
        # avoid publishing incidental personal information
        if re.search(r"身分證|住址|地址|電話|手機|配偶|出生|生日|前科|涉案|@|https?://",line): continue
        labels=[t["label"] for t in topics if any(w in line for w in t["terms"])]
        measures=[w for w in MEASURES if w in line]
        values=list(dict.fromkeys(x.group(0).replace(" ","") for x in AMOUNT.finditer(line)))[:5]
        if not labels or not measures: continue
        item={"topics":labels,"measures":measures,"values":values}
        if item not in out: out.append(item)
    return out[:24]

def build(conn, root=ROOT):
    exact=roster_index(root)
    normalized=collections.defaultdict(list)
    for k,rows in exact.items(): normalized[norm_key(k)].extend(rows)
    first=stage(conn,exact)
    matched=dict(first["records"])
    conn.row_factory=sqlite3.Row
    rows=conn.execute("""SELECT c.name,c.district,b.* FROM candidate_bulletin_profiles b
       JOIN candidates c USING(candidate_id) WHERE b.election_id BETWEEN 77 AND 82 AND c.election_id=b.election_id""").fetchall()
    row_map={}
    excluded=[]
    # Count all potential normalized source identities, not just candidates not yet matched.
    counts=collections.Counter(norm_key(("chief" if b["election_id"] in (77,78) else "council",b["district"],b["ballot_no"],b["name"])) for b in rows)
    for b in rows:
        key=("chief" if b["election_id"] in (77,78) else "council",b["district"],b["ballot_no"],b["name"])
        candidates=exact.get(key,[])
        is_exact=len(candidates)==1
        hits=candidates if is_exact else normalized.get(norm_key(key),[])
        if not isinstance(b["ballot_no"],int) or b["ballot_no"]<1 or len(hits)!=1 or hits[0].get("source_conflict") or not official_url(b["source_url"]) or not isinstance(b["source_page"],int) or b["source_page"]<1 or (not is_exact and counts[norm_key(key)]!=1):
            excluded.append({"name":b["name"],"district":b["district"],"number":b["ballot_no"],"reason":"missing_or_conflicting_identity_or_source"})
            continue
        r=hits[0]; k=r["id"]
        if not is_exact and k in matched:
            excluded.append({"name":b["name"],"district":b["district"],"number":b["ballot_no"],"reason":"already_matched"})
            continue
        if k in row_map: raise ValueError("duplicate matched source "+k)
        row_map[k]=(b,"exact" if is_exact else "format_normalized")
        if k not in matched:
            policy=[]
            for p in conn.execute("SELECT content,content_raw,source_url,note FROM platforms WHERE candidate_id=? AND election_id=? ORDER BY seq",(b["candidate_id"],b["election_id"])):
                if p["source_url"]==b["source_url"] and p["content"] and p["content"]==p["content_raw"] and "公報原文照抄" in (p["note"] or ""): policy.append(p["content"])
            matched[k]={"name":r["name"],"number":r["number"],"district":b["district"],"source_url":b["source_url"],"source_page":b["source_page"],"source_kind":b["source_kind"],"party_raw":b["party_raw"],"education":strings(b["education"]),"career":strings(b["career"]),"policy":policy,"status":"review_required"}
    if len(row_map)!=len(matched) or len(matched)+len(excluded)!=len(rows): raise ValueError("match accounting")
    topics=json.loads((root/"data/policy-topics.json").read_text())["topics"]
    details={}
    for k,x in matched.items():
        b,method=row_map[k]
        w,h=b["photo_width"],b["photo_height"]
        photo={"width":w,"height":h} if isinstance(w,int) and isinstance(h,int) and 0<w<=20000 and 0<h<=20000 else None
        details[k]={"name":x["name"],"number":x["number"],"source":x["source_url"],"page":x["source_page"],"match":method,"photo_metadata":photo,"policy_details":policy_details("\n".join(x["policy"]),topics)}
    stats={"source_rows":len(rows),"exact":len(first["records"]),"normalized_added":len(matched)-len(first["records"]),"matched":len(matched),"excluded":len(excluded),"photo_metadata":sum(bool(x["photo_metadata"]) for x in details.values()),"policy_details":sum(bool(x["policy_details"]) for x in details.values()),"policy_numeric":sum(any(y["values"] for y in x["policy_details"]) for x in details.values())}
    if stats["matched"]<1414: raise ValueError("coverage regression")
    first["records"]=matched
    return first,{"version":"0.1.16","source":{"repository":ORIGIN,"notice":"公報轉錄與圖檔尺寸資料；無照片重製或實質身分覆核。政策欄只表示同一文字片段出現的主題、措施字詞與數字，非承諾判定。"},"stats":stats,"records":details,"excluded":excluded}

def main():
    p=argparse.ArgumentParser();p.add_argument("--db",type=Path);a=p.parse_args()
    with tempfile.TemporaryDirectory() as t:
        db=a.db or Path(t)/"source.sqlite"
        if not a.db:
            with urllib.request.urlopen(urllib.request.Request(URL,headers={"User-Agent":"CivicLens"}),timeout=60) as r: data=r.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES or not data.startswith(b"SQLite format 3\x00"): raise ValueError("bad snapshot")
            db.write_bytes(data)
        if db.stat().st_size>MAX_BYTES: raise ValueError("oversized snapshot")
        with sqlite3.connect(db.resolve().as_uri()+"?mode=ro&immutable=1",uri=True) as conn:
            conn.execute("PRAGMA query_only=ON")
            stage_data,extra=build(conn)
        sha=hashlib.sha256(db.read_bytes()).hexdigest()
        stage_data["source"]["sha256"]=sha;extra["source"]["sha256"]=sha
        facts=derive(stage_data)
        old=json.loads((ROOT/"data/bulletin-facts.json").read_text())
        if any(facts["records"].get(k)!=v for k,v in old["records"].items()): raise ValueError("previous facts changed")
        for name,obj in (("bulletin-facts",facts),("bulletin-details",extra)):
            (ROOT/"data"/(name+".json")).write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n")
        print(json.dumps({"details":extra["stats"],"facts":facts["stats"]},ensure_ascii=False))
if __name__=="__main__":main()
