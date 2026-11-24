"""Build a pre-election claim review queue, not a verified promise ledger."""
import collections, datetime, hashlib, json, re, unicodedata
from pathlib import Path
from import_chief_sources import ROOT, SLUGS, REPO, load, safe_url
CUTOFF="2026-11-24"
KINDS={"政策承諾","成果陳述"}
# Fixed action and policy-object lexicons; only labels and literal numeric facts are published.
ACTIONS=("增設","新建","興建","擴建","設置","開辦","開放","改善","延長","提高","調高","提升","降低","減免","減少","補助","津貼","免費","擴大","增加","提供","推動","建立","完成","取消","整建","修繕","汰換","發放")
OBJECTS=("社會住宅","社宅","租金補貼","租屋","托育","托嬰","幼兒園","育兒","生育","長照","敬老","營養午餐","校舍","學校","捷運","輕軌","公車","道路","停車場","人行道","自行車","交通","污水","下水道","排水","防洪","垃圾","焚化爐","公園","綠地","醫療","醫院","診所","消防","警政","運動中心","圖書館","文化","觀光","市場","產業園區","青年","就業","農業","漁業","電費","水費","電動車","充電站","再生能源","公共工程","偏鄉","無障礙","防災")
UNITS=r"億元|萬元|千元|元|公里|公尺|公頃|個月|年|小時|分鐘|班次|席|戶|人|名|處|座|所|班|棟|間|件|輛|%|％"
NUM=re.compile(r"(?<![\d.])(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?\s*(?:"+UNITS+r")(?!\d)")
PRIVATE=re.compile(r"身分證|身份證|住址|電話|手機|生日|出生|配偶|子女|涉案|前科|罹患|電子郵件|@")
def norm(s):return re.sub(r"\s+","",unicodedata.normalize("NFKC",s))
def short_label(s):
    # A short neutral question label, not summary/quote or any long source prose.
    return isinstance(s,str) and 2<=len(s)<=22 and not PRIVATE.search(s) and bool(re.fullmatch(r"[\u3400-\u9fffA-Za-z0-9、／/與及（）() %％＋+－· -]+",s))
def tokens(quote):
    q=unicodedata.normalize("NFKC",quote)
    if PRIVATE.search(q):return [],[],[]
    acts=[x for x in ACTIONS if x in q]
    objs=[x for x in OBJECTS if x in q]
    nums=list(dict.fromkeys(re.sub(r"\s+","",m.group()) for m in NUM.finditer(q)))[:8]
    return acts,objs,nums
def valid_date(s):
    try:
        d=datetime.date.fromisoformat(s[:10])
        return s[:10] if d.year==2026 and s[:10]<=CUTOFF else None
    except (ValueError,TypeError,AttributeError):return None
def extract(data,candidates):
    index={(r["number"],r["name"]):r for r in candidates if not r.get("source_conflict")}
    matches={c["id"]:index[(c["number"],c["name"])] for c in data["candidates"] if (c["number"],c["name"]) in index}
    sources={s["id"]:s for s in data["sources"]}
    records={}; seen=set(); skipped=collections.Counter()
    for c in data["claims"]:
        if c.get("assertionType") not in KINDS:continue
        r=matches.get(c["candidateId"]);s=sources.get(c["sourceId"])
        if not r or not s or s.get("candidateId")!=c["candidateId"] or not safe_url(s.get("url")):
            skipped["identity_or_source"]+=1;continue
        q=c.get("quote","");raw=s.get("text","")
        if not q or not norm(q) or norm(q) not in norm(raw):
            skipped["quote_not_found"]+=1;continue
        date=valid_date(s.get("postedAt"))
        if not date:
            skipped["date_missing_or_outside_cutoff"]+=1;continue
        topic=c.get("topic");sub=c.get("subtopic")
        if not short_label(topic) or not short_label(sub):
            skipped["label_invalid"]+=1;continue
        acts,objs,nums=tokens(q)
        if not acts or not objs:
            skipped["no_specific_action_object"]+=1;continue
        kind=c["assertionType"]
        digest=hashlib.sha256(norm(q).encode()).hexdigest()
        # Reposts with identical normalized quote for the same candidate and type deduplicate.
        key=(r["id"],kind,digest)
        if key in seen:skipped["duplicate_quote"]+=1;continue
        seen.add(key)
        rid=hashlib.sha256(("|".join(key)).encode()).hexdigest()[:24]
        records[rid]={"candidate_id":r["id"],"name":r["name"],"number":r["number"],"type":kind,"topic":topic,"item":sub,"actions":acts,"objects":objs,"numbers":nums,"source":s["url"],"date":date,"quote_sha256":digest,"review_status":"待原文人工核對","tracking_status":"尚未建立履行判定" if kind=="政策承諾" else None}
    return records,skipped
def main():
    districts=[d for f in ("published-roster","national-roster-supplement") for d in json.loads((ROOT/"data"/(f+".json")).read_text())["districts"] if d["office"]=="chief"]
    by={d["county"]:d["candidates"] for d in districts}
    records={};skipped=collections.Counter();snapshots={}
    for i,slug in enumerate(SLUGS,1):
        x,sha=load(slug);rows,rej=extract(x,by[f"{i:02}"])
        if set(records)&set(rows):raise ValueError("duplicate id")
        records.update(rows);skipped.update(rej);snapshots[slug]=sha
    stats={"counties":len(snapshots),"records":len(records),"promise_leads":sum(x["type"]=="政策承諾" for x in records.values()),"performance_leads":sum(x["type"]=="成果陳述" for x in records.values()),"candidates":len({x["candidate_id"] for x in records.values()}),"promise_candidates":len({x["candidate_id"] for x in records.values() if x["type"]=="政策承諾"}),"with_numbers":sum(bool(x["numbers"]) for x in records.values()),"verified_promises":0,"verified_performance":0,"fulfillment_decisions":0}
    if stats["counties"]!=22 or stats["promise_leads"]<100:raise ValueError("coverage regression")
    result={"version":"0.1.18","cutoff":CUTOFF,"source":{"repository":REPO,"notice":"第三方政策分類及短議題標籤；本站校驗來源、引句存在性及日期，提取固定詞彙和數值。不發布原文或第三方摘要。尚非查證後的承諾清冊。"},"stats":stats,"skipped":dict(skipped),"snapshots":snapshots,"records":records}
    (ROOT/"data/policy-review-baseline.json").write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n")
    print(json.dumps({"stats":stats,"skipped":dict(skipped)},ensure_ascii=False))
    # Small review sample across counties; no raw source text or full summaries in logs.
    for k in sorted({x["candidate_id"][:2] for x in records.values()}):
        sample=next((x for x in records.values() if x["candidate_id"].startswith(k+"-") and x["type"]=="政策承諾" and x["numbers"]),None)
        if sample:print("sample",json.dumps(sample,ensure_ascii=False))
if __name__=="__main__":main()
