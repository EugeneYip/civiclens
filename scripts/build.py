from pathlib import Path
import json, html
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/election.json').read_text())
esc=html.escape
cards=''.join(f'<article class="county" data-name="{esc(c["name"])}" data-region="{esc(c["region"])}"><div><span class="eyebrow">{esc(c["region"])}</span><h3>{esc(c["name"])}</h3></div><a href="{esc(c["url"],quote=True)}" target="_blank" rel="noopener noreferrer">官方公報 <span aria-hidden="true">↗</span></a></article>' for c in d['counties'])
rows=''.join(f'<tr><th scope="row">{esc(x["office"])}</th><td>{x["seats"]:,}</td><td>{x["registered"]:,}</td><td>{x["candidates"]:,}</td></tr>' for x in d['offices'])
sources=''.join(f'<article class="source"><div><span class="eyebrow">{esc(s["agency"])} · {esc(s["type"])}</span><h3>{esc(s["title"])}</h3><p>{esc(s["description"])}</p></div><a href="{esc(s["url"],quote=True)}" target="_blank" rel="noopener noreferrer">原始來源 ↗</a></article>' for s in d['sources'])
page=(root/'scripts/template.html').read_text().replace('<!--COUNTIES-->',cards).replace('<!--ROWS-->',rows).replace('<!--SOURCES-->',sources).replace('<!--CSS-->',(root/'scripts/style.css').read_text()).replace('<!--JS-->',(root/'scripts/app.js').read_text())
(root/'index.html').write_text(page)
