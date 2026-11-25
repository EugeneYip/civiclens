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
page=(root/'scripts/template.html').read_text().replace('<!--COUNTIES-->',cards).replace('<!--ROWS-->',rows).replace('<!--SOURCES-->',sources).replace('<!--ELECTORS-->',elector_json).replace('<!--NATIONAL-->',national).replace('<!--CHIEF_SOURCES-->',chief_json).replace('<!--CSS-->',(root/'scripts/style.css').read_text()).replace('<!--JS-->',(root/'scripts/app.js').read_text()).replace('<!--VERSION-->',(root/'VERSION').read_text().strip())
(root/'index.html').write_text(page)
