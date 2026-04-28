from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from app.scraper import scrape_url

app = FastAPI(title="Web Scraper")


class ScrapeRequest(BaseModel):
    url: HttpUrl


class ScrapeResponse(BaseModel):
    url: str
    status_code: int
    metadata: dict
    text: list[dict]
    links: list[dict]
    images: list[dict]


@app.post("/api/scrape", response_model=ScrapeResponse)
async def api_scrape(req: ScrapeRequest):
    result = await scrape_url(str(req.url))
    return result


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Web Scraper</title>
<style>
  :root { --bg: #0f172a; --card: #1e293b; --accent: #38bdf8; --text: #e2e8f0; --muted: #94a3b8; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
  .container { max-width: 960px; margin: 0 auto; padding: 2rem 1rem; }
  h1 { text-align: center; font-size: 2rem; margin-bottom: 1.5rem; color: var(--accent); }
  .search-box { display: flex; gap: .5rem; margin-bottom: 2rem; }
  input[type="url"] { flex: 1; padding: .75rem 1rem; border: 1px solid #334155; border-radius: .5rem; background: var(--card); color: var(--text); font-size: 1rem; outline: none; }
  input[type="url"]:focus { border-color: var(--accent); }
  button { padding: .75rem 1.5rem; border: none; border-radius: .5rem; background: var(--accent); color: #0f172a; font-weight: 600; font-size: 1rem; cursor: pointer; }
  button:hover { opacity: .9; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  .tabs { display: flex; gap: .25rem; margin-bottom: 1rem; }
  .tab { padding: .5rem 1rem; border-radius: .5rem .5rem 0 0; background: var(--card); color: var(--muted); cursor: pointer; border: 1px solid transparent; }
  .tab.active { color: var(--accent); border-color: var(--accent); border-bottom-color: var(--card); }
  .panel { display: none; background: var(--card); border-radius: 0 .5rem .5rem .5rem; padding: 1.5rem; max-height: 70vh; overflow-y: auto; }
  .panel.active { display: block; }
  .meta-grid { display: grid; grid-template-columns: 140px 1fr; gap: .5rem; }
  .meta-label { color: var(--muted); font-size: .85rem; }
  .meta-value { word-break: break-all; }
  .text-block { margin-bottom: .75rem; }
  .text-block .tag { display: inline-block; background: #334155; color: var(--accent); padding: .1rem .4rem; border-radius: .25rem; font-size: .75rem; margin-right: .5rem; }
  .link-item, .img-item { padding: .5rem 0; border-bottom: 1px solid #334155; }
  .link-item a, .img-item a { color: var(--accent); text-decoration: none; word-break: break-all; }
  .link-item a:hover, .img-item a:hover { text-decoration: underline; }
  .link-text { color: var(--muted); font-size: .85rem; }
  .img-preview { max-width: 120px; max-height: 80px; border-radius: .25rem; margin-top: .25rem; }
  .spinner { display: none; text-align: center; padding: 2rem; color: var(--muted); }
  .error { color: #f87171; text-align: center; padding: 1rem; }
  .count { font-size: .8rem; color: var(--muted); margin-left: .25rem; }
  #results { display: none; }
</style>
</head>
<body>
<div class="container">
  <h1>&#128269; Web Scraper</h1>
  <div class="search-box">
    <input type="url" id="urlInput" placeholder="https://example.com" />
    <button id="scrapeBtn" onclick="doScrape()">Scrape</button>
  </div>
  <div class="spinner" id="spinner">Scraping...</div>
  <div class="error" id="error"></div>
  <div id="results">
    <div class="tabs">
      <div class="tab active" onclick="switchTab('metadata')">Metadata</div>
      <div class="tab" onclick="switchTab('text')">Text <span class="count" id="textCount"></span></div>
      <div class="tab" onclick="switchTab('links')">Links <span class="count" id="linksCount"></span></div>
      <div class="tab" onclick="switchTab('images')">Images <span class="count" id="imagesCount"></span></div>
      <div class="tab" onclick="switchTab('raw')">Raw JSON</div>
    </div>
    <div class="panel active" id="panel-metadata"></div>
    <div class="panel" id="panel-text"></div>
    <div class="panel" id="panel-links"></div>
    <div class="panel" id="panel-images"></div>
    <div class="panel" id="panel-raw"></div>
  </div>
</div>
<script>
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', t.textContent.trim().toLowerCase().startsWith(name)));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
}

async function doScrape() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) return;
  const btn = document.getElementById('scrapeBtn');
  const spinner = document.getElementById('spinner');
  const error = document.getElementById('error');
  const results = document.getElementById('results');
  btn.disabled = true; spinner.style.display = 'block'; error.textContent = ''; results.style.display = 'none';
  try {
    const res = await fetch('/api/scrape', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }
    const data = await res.json();
    renderMetadata(data.metadata, data.url, data.status_code);
    renderText(data.text);
    renderLinks(data.links);
    renderImages(data.images);
    document.getElementById('panel-raw').innerHTML = '<pre style="white-space:pre-wrap;font-size:.85rem;">' + escHtml(JSON.stringify(data, null, 2)) + '</pre>';
    results.style.display = 'block';
  } catch (e) { error.textContent = 'Error: ' + e.message; }
  finally { btn.disabled = false; spinner.style.display = 'none'; }
}

function renderMetadata(m, url, status) {
  let h = '<div class="meta-grid">';
  h += row('URL', '<a href="'+escAttr(url)+'" target="_blank">'+escHtml(url)+'</a>');
  h += row('Status', status);
  h += row('Title', m.title || '—');
  h += row('Description', m.description || '—');
  h += row('Keywords', m.keywords || '—');
  h += row('Canonical', m.canonical_url ? '<a href="'+escAttr(m.canonical_url)+'" target="_blank">'+escHtml(m.canonical_url)+'</a>' : '—');
  if (m.og_tags && Object.keys(m.og_tags).length) {
    for (const [k,v] of Object.entries(m.og_tags)) h += row('og:'+k, escHtml(v));
  }
  h += '</div>';
  document.getElementById('panel-metadata').innerHTML = h;
}
function row(label, value) { return '<div class="meta-label">'+escHtml(label)+'</div><div class="meta-value">'+value+'</div>'; }

function renderText(blocks) {
  document.getElementById('textCount').textContent = '(' + blocks.length + ')';
  let h = '';
  for (const b of blocks) h += '<div class="text-block"><span class="tag">'+b.tag+'</span>'+escHtml(b.text)+'</div>';
  document.getElementById('panel-text').innerHTML = h || '<em>No text found.</em>';
}

function renderLinks(links) {
  document.getElementById('linksCount').textContent = '(' + links.length + ')';
  let h = '';
  for (const l of links) h += '<div class="link-item"><a href="'+escAttr(l.href)+'" target="_blank">'+escHtml(l.href)+'</a>' + (l.text ? '<div class="link-text">'+escHtml(l.text)+'</div>' : '') + '</div>';
  document.getElementById('panel-links').innerHTML = h || '<em>No links found.</em>';
}

function renderImages(images) {
  document.getElementById('imagesCount').textContent = '(' + images.length + ')';
  let h = '';
  for (const img of images) h += '<div class="img-item"><a href="'+escAttr(img.src)+'" target="_blank">'+escHtml(img.src)+'</a>' + (img.alt ? '<div class="link-text">'+escHtml(img.alt)+'</div>' : '') + '<br><img class="img-preview" src="'+escAttr(img.src)+'" loading="lazy" onerror="this.style.display=\'none\'"/></div>';
  document.getElementById('panel-images').innerHTML = h || '<em>No images found.</em>';
}

function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function escAttr(s) { return s.replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }

document.getElementById('urlInput').addEventListener('keydown', e => { if (e.key === 'Enter') doScrape(); });
</script>
</body>
</html>
"""
