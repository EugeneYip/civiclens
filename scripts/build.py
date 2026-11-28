from pathlib import Path
import json, html
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/election.json').read_text())
esc=html.escape
cards=''.join(f'<article class="county" data-name="{esc(c["name"])}" data-region="{esc(c["region"])}"><a href="{esc(c["url"],quote=True)}" target="_blank" rel="noopener noreferrer" aria-label="{esc(c["name"])}官方電子公報（另開視窗）">{esc(c["name"])} <span aria-hidden="true">↗</span></a></article>' for c in d['counties'])
rows=''.join(f'<tr><th scope="row">{esc(x["office"])}</th><td>{x["seats"]:,}</td><td>{x["registered"]:,}</td><td>{x["candidates"]:,}</td></tr>' for x in d['offices'])
sources=''.join(f'<article class="source"><div><span class="eyebrow">{esc(s["agency"])} · {esc(s["type"])}</span><h3>{esc(s["title"])}</h3><p>{esc(s["description"])}</p></div><a href="{esc(s["url"],quote=True)}" target="_blank" rel="noopener noreferrer">原始來源 ↗</a></article>' for s in d['sources'])
electors=json.loads((root/'data/electors.json').read_text())
elector_json=json.dumps(electors,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
national=''.join(f'<div><span>{esc(label)}</span><strong>{n:,}</strong></div>' for label,n in zip(electors['labels'],electors['totals']))
chief=json.loads((root/'data/chief-sources.json').read_text())
chief_json=json.dumps(chief,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')

ref=json.loads((root/'data/referendum.json').read_text())
def render_ref(r):
    E=lambda x:esc(str(x))
    import re as _re
    def C(x):  # keep each clause together: break preferably after ，；
        parts=[p for p in _re.split(r'(?<=[，；。])(?=.)',str(x)) if p]
        return E(x) if len(parts)<2 else ''.join('<span class="clause">'+E(p)+'</span>' for p in parts)
    o=['<div class="sectionhead"><h2>全國性公投 · 第'+E(r['case'])+'案</h2></div>']
    o.append('<div class="ref-main"><p class="eyebrow">主文</p><p class="ref-question">'+C(r['question'])+'</p>')
    o.append('<dl class="ref-facts">')
    facts=[('投票日',r['vote']['date']+' '+r['vote']['time']),('公投票',r['vote']['ballot_color']+'，於「同意」或「不同意」上方圈選欄擇一圈選'),('提案',r['proposer']['body']+'（'+r['proposer']['basis']+'）'),('投票權人',f"{r['electorate']['count']:,}\u00a0人"),('通過門檻',f"有效同意票多於不同意票，且達 {r['threshold']['votes_needed']:,}\u00a0票以上")]
    for k,v in facts: o.append('<div><dt>'+E(k)+'</dt><dd>'+C(v)+'</dd></div>')
    o.append('</dl><p class="small">'+C(r['age_note'])+'</p></div>')
    o.append('<div id="ref-live" class="ref-live" hidden aria-live="polite"></div>')
    def note(x):
        if isinstance(x,str): return '<li>'+E(x)+'</li>'
        return '<li>'+E(x['text'])+'<ol class="ref-sub">'+''.join('<li>'+E(i)+'</li>' for i in x['items'])+'</ol></li>'
    # reason
    o.append('<details class="ref-block"><summary>理由書全文（'+E(r['reason']['by'])+'提出）</summary><div class="ref-reason">')
    for p in r['reason']['paragraphs']:
        tag={'heading':'h3','item':'p','para':'p'}[p['kind']]; cls={'heading':'ref-h','item':'ref-item','para':''}[p['kind']]
        o.append(f'<{tag}'+(f' class="{cls}"' if cls else '')+'>'+E(p['text'])+f'</{tag}>')
    o.append('<p class="small">出處：<span class="nw">中選會'+E(r['announcement']['date'])+'公告</span><span class="nw">（'+E(r['announcement']['no'])+'）</span></p></div></details>')
    # hearings
    o.append('<details class="ref-block" open><summary>正反方意見發表會（'+str(len(r['hearings']))+' 場）</summary><p class="small">'+C(r['hearings_note'])+'</p><div class="ref-hearings">')
    for h in r['hearings']:
        o.append('<article class="ref-hearing"><div class="ref-hmeta"><strong>第'+E(h['no'])+'場</strong><span>'+E(h['date'])+'・'+E(h['channel'])+'</span></div>')
        o.append('<dl class="ref-sides"><div><dt>正方</dt><dd>'+E(h['pro'])+'</dd></div><div><dt>反方</dt><dd>'+E(h['con'])+'</dd></div><div><dt>主持</dt><dd>'+E(h['host'])+'</dd></div></dl>')
        o.append('<div class="video-slot"><button type="button" class="video-play ref-play" data-video="'+E(h['video'])+'" data-title="'+E(r['title']+'意見發表會第'+str(h['no'])+'場')+'" aria-label="站內播放：第'+E(h['no'])+'場意見發表會"><img class="video-thumb" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" src="https://i.ytimg.com/vi/'+E(h['video'])+'/mqdefault.jpg"><span class="video-play-icon" aria-hidden="true">▶</span></button></div></article>')
    o.append('</div></details>')
    # threshold
    o.append('<details class="ref-block"><summary>通過門檻與通過後效果</summary>')
    o.append('<p><strong>'+E(r['threshold']['law'])+'</strong>：'+E(r['threshold']['text'])+E(r['threshold']['fail_text'])+'</p>')
    o.append(f"<p>投票權人 {r['electorate']['count']:,} 人之四分之一為 {r['electorate']['count']/4:,.2f}，故有效同意票須達 {r['threshold']['votes_needed']:,} 票以上。"+E(r['threshold']['note'])+'</p>')
    o.append('<p><strong>'+E(r['effect']['law'])+'</strong>：'+E(r['effect']['text'])+'</p></details>')
    # how to vote
    o.append('<details class="ref-block"><summary>誰可以投、怎麼投</summary><h3 class="ref-h">投票權人資格</h3><p>'+E(r['eligibility'])+'</p><h3 class="ref-h">投票地點與攜帶證件</h3><p>投票地點：'+E(r['vote']['place'])+'。'+E(r['bring'])+'</p>')
    o.append('<h3 class="ref-h">投票流程</h3><ol class="ref-steps">'+''.join('<li><strong>'+E(a)+'</strong>'+E(b)+'</li>' for a,b in r['steps'])+'</ol>')
    o.append('<h3 class="ref-h">公投票式樣與圈選</h3><div class="ref-ballot-row"><figure class="ref-ballot"><div class="rb" aria-hidden="true"><div class="rb-box"></div><div class="rb-box"></div><div class="rb-opt">同意</div><div class="rb-opt">不同意</div><div class="rb-no">'+E(r['case'])+'</div><div class="rb-q">'+E(r['question'])+'</div></div><figcaption class="small">公投票'+E(r['vote']['ballot_color'])+'。使用選舉委員會製備之圈選工具，於「同意」或「不同意」上方圈選欄擇一圈蓋（依公投公報第五項式樣簡化重繪）。</figcaption></figure>')
    o.append('<div><p class="ref-label">下列情形之一者，公投票無效：</p><ul class="profile-list">'+''.join('<li>'+E(x)+'</li>' for x in r['invalid'])+'</ul></div></div>')
    o.append('<h3 class="ref-h">投票所內注意事項</h3><ul class="profile-list">'+''.join(note(x) for x in r['notes'])+'</ul>')
    o.append('<h3 class="ref-h">罰則摘錄</h3><ul class="profile-list">'+''.join('<li><strong>'+E(x['law'])+'</strong>：'+E(x['text'])+'</li>' for x in r['penalties'])+'</ul><p class="small">'+E(r['penalties_note'])+'</p></details>')
    o.append('<div class="ref-sources"><p class="small">資料來源（'+E(r['checked_on'])+' 核對）</p><ul>'+''.join('<li><a href="'+esc(s['url'],quote=True)+'" target="_blank" rel="noopener noreferrer">'+E(s['title'])+'\u00a0↗</a></li>' for s in r['sources'])+'</ul></div>')
    return ''.join(o)
referendum_html=render_ref(ref)
page=(root/'scripts/template.html').read_text().replace('<!--COUNTIES-->',cards).replace('<!--ROWS-->',rows).replace('<!--SOURCES-->',sources).replace('<!--ELECTORS-->',elector_json).replace('<!--NATIONAL-->',national).replace('<!--REFERENDUM-->',referendum_html).replace('<!--CHIEF_SOURCES-->',chief_json).replace('<!--CSS-->',(root/'scripts/style.css').read_text()).replace('<!--JS-->',(root/'scripts/app.js').read_text()+'\n'+(root/'scripts/phrase.js').read_text()).replace('<!--VERSION-->',(root/'VERSION').read_text().strip())
(root/'index.html').write_text(page)
