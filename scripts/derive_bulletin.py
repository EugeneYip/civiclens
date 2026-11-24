"""Derive limited factual profile data and keyword index from a staged bulletin snapshot."""
import argparse
import json
import re
from pathlib import Path
from stage_bulletin import ROOT, ORIGIN, official_url, roster_index

PRIVATE = re.compile(r"身分證|身份證|住址|地址|電話|手機|電子郵件|配偶|子女|出生|生日|病史|罹患|疾病|信仰|宗教|前科|刑事|判刑|犯罪|涉案|貪污|[0-9]{5,}|@|https?://")
EDUCATION = re.compile(r"大學|學院|研究所|高中|高職|中學|國中|國小|小學|專科|博士|碩士|學士|畢業|肄業|學校")
CAREER = re.compile(r"議員|縣長|市長|鄉長|鎮長|里長|村長|代表|委員|主任|處長|局長|科長|校長|教師|教授|講師|董事|經理|理事|會長|執行長|秘書|顧問|專員|工程師|醫師|律師|會計師|公務員|負責人|助理|研究員|社工|護理師")
PARTY = re.compile(r"^[\u3400-\u9fffA-Za-z0-9．・· ()（）]{1,36}$")
def facts(lines, pattern):
    return list(dict.fromkeys(x for x in lines if 2 <= len(x) <= 55 and pattern.search(x) and not PRIVATE.search(x) and not re.search(r"[。！？!?#<>]",x)))[:16]

def derive(staged, root=ROOT):
    if staged["source"]["repository"] != ORIGIN:
        raise ValueError("unexpected upstream")
    roster={r["id"]:r for rows in roster_index(root).values() for r in rows}
    topics=json.loads((root/"data/policy-topics.json").read_text())["topics"]
    records={}
    for k,x in staged["records"].items():
        r=roster.get(k)
        if not r or r["name"]!=x["name"] or r["number"]!=x["number"] or r.get("source_conflict") or not official_url(x["source_url"]) or not isinstance(x["source_page"],int) or x["source_page"]<1:
            raise ValueError("identity or source drift "+k)
        edu=facts(x["education"],EDUCATION)
        career=facts(x["career"],CAREER)
        policy="\n".join(x["policy"])
        labels={t["label"]:[w for w in t["terms"] if w in policy] for t in topics}
        labels={k:v for k,v in labels.items() if v}
        party=(x["party_raw"] or "").strip()
        if not PARTY.fullmatch(party) or PRIVATE.search(party): party=None
        records[k]={"name":r["name"],"number":r["number"],"source":x["source_url"],"page":x["source_page"],"education":edu,"career":career,"party":party,"topics":labels,"text_available":bool(policy),"status":"secondary_bulletin_transcription"}
    stats={"matched":len(records),"education":sum(bool(x["education"]) for x in records.values()),"career":sum(bool(x["career"]) for x in records.values()),"party":sum(bool(x["party"]) for x in records.values()),"policy_text_source":sum(x["text_available"] for x in records.values()),"policy_topics":sum(bool(x["topics"]) for x in records.values())}
    if stats["matched"]<1000 or stats["policy_topics"]<500:
        raise ValueError("coverage gate "+str(stats))
    return {"version":"0.1.15","source":{"repository":ORIGIN,"sha256":staged["source"]["sha256"],"credit":"正至 · 台灣選舉資訊平台／中選會公報","method":"第三方 OCR 轉錄，姓名與號次配對；短學經歷與固定主題字詞，非獨立人工覆核。"},"stats":stats,"records":records}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("stage",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args()
    result=derive(json.loads(a.stage.read_text()))
    a.output.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n")
    print(json.dumps(result["stats"],ensure_ascii=False))
if __name__=="__main__": main()
