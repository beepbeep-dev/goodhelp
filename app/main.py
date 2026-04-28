from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl

from app.scraper import scrape_url
from app.searcher import search_web, search_pastes, deep_search

app = FastAPI(title="Web Scraper")


class ScrapeRequest(BaseModel):
    url: HttpUrl


class SearchScrapeRequest(BaseModel):
    query: str
    num_results: int = 5


class PasteSearchRequest(BaseModel):
    query: str
    num_results: int = 10


class DeepSearchRequest(BaseModel):
    query: str
    num_results: int = 5
    max_depth_links: int = 3


@app.post("/api/scrape")
async def api_scrape(req: ScrapeRequest):
    result = await scrape_url(str(req.url))
    return result


@app.post("/api/search")
async def api_search(req: SearchScrapeRequest):
    results = await search_web(req.query, req.num_results)
    return {"query": req.query, "results": results}


@app.post("/api/search-and-scrape")
async def api_search_and_scrape(req: SearchScrapeRequest):
    search_results = await search_web(req.query, req.num_results)
    scraped = []
    for sr in search_results:
        try:
            data = await scrape_url(sr["url"])
            scraped.append({
                "search_result": sr,
                "scrape": data,
                "error": None,
            })
        except Exception as e:
            scraped.append({
                "search_result": sr,
                "scrape": None,
                "error": str(e),
            })
    return {"query": req.query, "results": scraped}


@app.post("/api/paste-search")
async def api_paste_search(req: PasteSearchRequest):
    search_results = await search_pastes(req.query, req.num_results)
    scraped = []
    for sr in search_results:
        try:
            data = await scrape_url(sr["url"])
            scraped.append({
                "search_result": sr,
                "scrape": data,
                "error": None,
            })
        except Exception as e:
            scraped.append({
                "search_result": sr,
                "scrape": None,
                "error": str(e),
            })
    return {"query": req.query, "results": scraped}


@app.post("/api/deep-search")
async def api_deep_search(req: DeepSearchRequest):
    return await deep_search(req.query, req.num_results, req.max_depth_links)


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
  :root { --bg: #0f172a; --card: #1e293b; --accent: #38bdf8; --text: #e2e8f0; --muted: #94a3b8; --green: #4ade80; --red: #f87171; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
  .container { max-width: 1060px; margin: 0 auto; padding: 2rem 1rem; }
  h1 { text-align: center; font-size: 2rem; margin-bottom: .5rem; color: var(--accent); }
  .subtitle { text-align: center; color: var(--muted); margin-bottom: 1.5rem; font-size: .9rem; }
  .mode-toggle { display: flex; justify-content: center; gap: .5rem; margin-bottom: 1.5rem; }
  .mode-btn { padding: .5rem 1.25rem; border: 1px solid #334155; border-radius: .5rem; background: var(--card); color: var(--muted); cursor: pointer; font-size: .9rem; }
  .mode-btn.active { color: var(--accent); border-color: var(--accent); }
  .search-box { display: flex; gap: .5rem; margin-bottom: 1.5rem; }
  .search-box input { flex: 1; padding: .75rem 1rem; border: 1px solid #334155; border-radius: .5rem; background: var(--card); color: var(--text); font-size: 1rem; outline: none; }
  .search-box input:focus { border-color: var(--accent); }
  .search-box button { padding: .75rem 1.5rem; border: none; border-radius: .5rem; background: var(--accent); color: #0f172a; font-weight: 600; font-size: 1rem; cursor: pointer; white-space: nowrap; }
  .search-box button:hover { opacity: .9; }
  .search-box button:disabled { opacity: .5; cursor: not-allowed; }
  .spinner { display: none; text-align: center; padding: 2rem; color: var(--muted); }
  .error { color: var(--red); text-align: center; padding: 1rem; }

  /* Search results list */
  .sr-list { margin-bottom: 1.5rem; }
  .sr-card { background: var(--card); border-radius: .5rem; padding: 1rem 1.25rem; margin-bottom: .75rem; border-left: 3px solid var(--accent); cursor: pointer; transition: border-color .15s; }
  .sr-card:hover { border-left-color: var(--green); }
  .sr-card.has-error { border-left-color: var(--red); }
  .sr-card.expanded { border-left-color: var(--green); }
  .sr-title { font-weight: 600; margin-bottom: .25rem; }
  .sr-url { color: var(--muted); font-size: .8rem; word-break: break-all; margin-bottom: .25rem; }
  .sr-snippet { font-size: .85rem; color: var(--muted); }
  .sr-status { font-size: .75rem; margin-top: .5rem; }
  .sr-status.ok { color: var(--green); }
  .sr-status.fail { color: var(--red); }

  /* Scrape detail panel */
  .detail { display: none; margin-top: .75rem; padding-top: .75rem; border-top: 1px solid #334155; }
  .detail.open { display: block; }
  .tabs { display: flex; gap: .25rem; margin-bottom: .75rem; }
  .tab { padding: .4rem .75rem; border-radius: .5rem .5rem 0 0; background: #0f172a; color: var(--muted); cursor: pointer; border: 1px solid transparent; font-size: .85rem; }
  .tab.active { color: var(--accent); border-color: var(--accent); border-bottom-color: #0f172a; }
  .panel { display: none; background: #0f172a; border-radius: 0 .5rem .5rem .5rem; padding: 1rem; max-height: 50vh; overflow-y: auto; font-size: .85rem; }
  .panel.active { display: block; }
  .meta-grid { display: grid; grid-template-columns: 130px 1fr; gap: .4rem; }
  .meta-label { color: var(--muted); font-size: .8rem; }
  .meta-value { word-break: break-all; }
  .text-block { margin-bottom: .5rem; }
  .text-block .tag { display: inline-block; background: #334155; color: var(--accent); padding: .1rem .4rem; border-radius: .25rem; font-size: .7rem; margin-right: .4rem; }
  .link-item, .img-item { padding: .4rem 0; border-bottom: 1px solid #1e293b; }
  .link-item a, .img-item a { color: var(--accent); text-decoration: none; word-break: break-all; }
  .link-text { color: var(--muted); font-size: .8rem; }
  .img-preview { max-width: 100px; max-height: 60px; border-radius: .25rem; margin-top: .25rem; }
  .count { font-size: .75rem; color: var(--muted); margin-left: .2rem; }
  #results { display: none; }

  /* URL mode single result */
  .single-result { background: var(--card); border-radius: .5rem; padding: 1.25rem; }
</style>
</head>
<body>
<div class="container">
  <h1>&#128269; Web Scraper</h1>
  <p class="subtitle">Search for anything or paste a URL — it finds and scrapes automatically</p>

  <div class="mode-toggle">
    <div class="mode-btn active" onclick="setMode('search')" id="mode-search">Search &amp; Scrape</div>
    <div class="mode-btn" onclick="setMode('paste')" id="mode-paste">Cool Mode &#128526;</div>
    <div class="mode-btn" onclick="setMode('deep')" id="mode-deep">Deep Search &#128373;</div>
    <div class="mode-btn" onclick="setMode('url')" id="mode-url">Scrape URL</div>
  </div>

  <div class="search-box">
    <input type="text" id="mainInput" placeholder="What are you looking for?" />
    <button id="goBtn" onclick="doAction()">Search &amp; Scrape</button>
  </div>

  <div class="spinner" id="spinner">Working...</div>
  <div class="error" id="error"></div>
  <div id="results"></div>
</div>

<script>
let currentMode = 'search';
const BASE = window.location.origin;

function setMode(mode) {
  currentMode = mode;
  document.getElementById('mode-search').classList.toggle('active', mode === 'search');
  document.getElementById('mode-paste').classList.toggle('active', mode === 'paste');
  document.getElementById('mode-deep').classList.toggle('active', mode === 'deep');
  document.getElementById('mode-url').classList.toggle('active', mode === 'url');
  const input = document.getElementById('mainInput');
  const btn = document.getElementById('goBtn');
  if (mode === 'search') {
    input.type = 'text';
    input.placeholder = 'What are you looking for?';
    btn.textContent = 'Search & Scrape';
  } else if (mode === 'paste') {
    input.type = 'text';
    input.placeholder = 'Keywords to search pastes, Telegram, Discord...';
    btn.textContent = 'Search Everything';
  } else if (mode === 'deep') {
    input.type = 'text';
    input.placeholder = 'Deep search — follows links to dig deeper...';
    btn.textContent = 'Deep Search';
  } else {
    input.type = 'url';
    input.placeholder = 'https://example.com';
    btn.textContent = 'Scrape';
  }
  document.getElementById('results').style.display = 'none';
  document.getElementById('error').textContent = '';
}

async function doAction() {
  const val = document.getElementById('mainInput').value.trim();
  if (!val) return;
  if (currentMode === 'url') return doScrapeUrl(val);
  if (currentMode === 'paste') return doPasteSearch(val);
  if (currentMode === 'deep') return doDeepSearch(val);
  return doSearchScrape(val);
}

async function doPasteSearch(query) {
  const btn = document.getElementById('goBtn');
  const spinner = document.getElementById('spinner');
  const error = document.getElementById('error');
  const results = document.getElementById('results');
  btn.disabled = true; spinner.style.display = 'block'; error.textContent = ''; results.style.display = 'none';
  try {
    const res = await fetch(BASE + '/api/paste-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, num_results: 10 })
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }
    const data = await res.json();
    renderPasteResults(data);
    results.style.display = 'block';
  } catch (e) { error.textContent = 'Error: ' + e.message; }
  finally { btn.disabled = false; spinner.style.display = 'none'; }
}

async function doSearchScrape(query) {
  const btn = document.getElementById('goBtn');
  const spinner = document.getElementById('spinner');
  const error = document.getElementById('error');
  const results = document.getElementById('results');
  btn.disabled = true; spinner.style.display = 'block'; error.textContent = ''; results.style.display = 'none';
  try {
    const res = await fetch(BASE + '/api/search-and-scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, num_results: 5 })
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }
    const data = await res.json();
    renderSearchResults(data);
    results.style.display = 'block';
  } catch (e) { error.textContent = 'Error: ' + e.message; }
  finally { btn.disabled = false; spinner.style.display = 'none'; }
}

async function doScrapeUrl(url) {
  const btn = document.getElementById('goBtn');
  const spinner = document.getElementById('spinner');
  const error = document.getElementById('error');
  const results = document.getElementById('results');
  btn.disabled = true; spinner.style.display = 'block'; error.textContent = ''; results.style.display = 'none';
  try {
    const res = await fetch(BASE + '/api/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }
    const data = await res.json();
    results.innerHTML = '<div class="single-result">' + buildScrapeDetail(data, 'single') + '</div>';
    results.style.display = 'block';
    switchTab('single', 'metadata');
  } catch (e) { error.textContent = 'Error: ' + e.message; }
  finally { btn.disabled = false; spinner.style.display = 'none'; }
}

async function doDeepSearch(query) {
  const btn = document.getElementById('goBtn');
  const spinner = document.getElementById('spinner');
  const error = document.getElementById('error');
  const results = document.getElementById('results');
  btn.disabled = true; spinner.style.display = 'block'; error.textContent = ''; results.style.display = 'none';
  spinner.innerHTML = 'Deep searching... scraping pages and following links \u26a1';
  try {
    const res = await fetch(BASE + '/api/deep-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, num_results: 5, max_depth_links: 3 })
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }
    const data = await res.json();
    renderDeepResults(data);
    results.style.display = 'block';
  } catch (e) { error.textContent = 'Error: ' + e.message; }
  finally { btn.disabled = false; spinner.style.display = 'none'; spinner.innerHTML = 'Working...'; }
}

function renderDeepResults(data) {
  const el = document.getElementById('results');
  const st = data.stats;
  let h = '<div style="background:#1e293b;padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1rem;font-size:.85rem;display:flex;gap:1.5rem;flex-wrap:wrap">';
  h += '<span style="color:var(--accent)">&#128269; Searched: <b>' + st.pages_searched + '</b> pages</span>';
  h += '<span style="color:var(--green)">&#128196; Scraped: <b>' + st.pages_scraped + '</b></span>';
  h += '<span style="color:#c084fc">&#128279; Links followed: <b>' + st.links_followed + '</b></span>';
  h += '<span style="color:var(--muted)">Total links found: ' + st.total_links_found + '</span>';
  h += '</div>';

  if (data.results.length) {
    h += '<div style="font-size:.8rem;color:var(--accent);margin-bottom:.5rem;text-transform:uppercase;letter-spacing:.05em">Depth 0 — Direct Results</div>';
    h += '<div class="sr-list">';
    data.results.forEach((r, i) => {
      h += buildDeepCard(r, i, false);
    });
    h += '</div>';
  }

  if (data.deep_results && data.deep_results.length) {
    h += '<div style="font-size:.8rem;color:#c084fc;margin:.75rem 0 .5rem;text-transform:uppercase;letter-spacing:.05em">Depth 1 \u2014 Followed Links &#128279;</div>';
    h += '<div class="sr-list">';
    data.deep_results.forEach((r, i) => {
      h += buildDeepCard(r, 'd' + i, true);
    });
    h += '</div>';
  }

  if (!data.results.length && (!data.deep_results || !data.deep_results.length)) {
    h += '<div style="text-align:center;color:var(--muted);padding:2rem;">No results found.</div>';
  }

  el.innerHTML = h;
}

function buildDeepCard(r, idx, isDeep) {
  const sr = r.search_result;
  const hasError = !!r.error;
  const borderColor = isDeep ? '#c084fc' : 'var(--accent)';
  let c = '<div class="sr-card' + (hasError ? ' has-error' : '') + '" onclick="toggleDetail(\\'' + idx + '\\')" style="border-left-color:' + borderColor + '">';
  c += '<div style="display:flex;justify-content:space-between;align-items:center"><div class="sr-title">' + escHtml(sr.title) + '</div>';
  if (isDeep) c += '<span style="font-size:.7rem;background:#334155;padding:.2rem .5rem;border-radius:.25rem;color:#c084fc">depth 1</span>';
  c += '</div>';
  c += '<div class="sr-url"><a href="'+escAttr(sr.url)+'" target="_blank" onclick="event.stopPropagation()" style="color:var(--accent)">' + escHtml(sr.url) + '</a></div>';
  if (sr.snippet) c += '<div class="sr-snippet">' + escHtml(sr.snippet) + '</div>';
  if (hasError) {
    c += '<div class="sr-status fail">Failed to scrape: ' + escHtml(r.error) + '</div>';
  } else if (r.scrape) {
    const s = r.scrape;
    c += '<div class="sr-status ok">Scraped: ' + s.text.length + ' text blocks, ' + s.links.length + ' links, ' + s.images.length + ' images</div>';
  }
  if (r.scrape) {
    c += '<div class="detail" id="detail-' + idx + '">' + buildScrapeDetail(r.scrape, 'r' + idx) + '</div>';
  }
  c += '</div>';
  return c;
}

const SOURCE_COLORS = {
  telegram: '#26A5E4',
  discord: '#5865F2',
};

function badgeColor(source) {
  return SOURCE_COLORS[source] || '#a78bfa';
}

function renderPasteResults(data) {
  const el = document.getElementById('results');
  if (!data.results.length) {
    el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:2rem;">No results found for that query. Try different keywords.</div>';
    return;
  }
  let h = '<div class="sr-list">';
  data.results.forEach((r, i) => {
    const sr = r.search_result;
    const hasError = !!r.error;
    const bc = badgeColor(sr.source);
    h += '<div class="sr-card' + (hasError ? ' has-error' : '') + '" onclick="toggleDetail(' + i + ')" style="border-left-color:' + bc + '">';
    h += '<div style="display:flex;justify-content:space-between;align-items:center"><div class="sr-title">' + escHtml(sr.title) + '</div>';
    h += '<span style="font-size:.7rem;background:#334155;padding:.2rem .5rem;border-radius:.25rem;color:' + bc + '">' + escHtml(sr.source) + '</span></div>';
    h += '<div class="sr-url"><a href="'+escAttr(sr.url)+'" target="_blank" onclick="event.stopPropagation()" style="color:var(--accent)">' + escHtml(sr.url) + '</a></div>';
    if (sr.snippet) h += '<div class="sr-snippet">' + escHtml(sr.snippet) + '</div>';
    if (hasError) {
      h += '<div class="sr-status fail">Could not scrape content: ' + escHtml(r.error) + '</div>';
    } else if (r.scrape) {
      const s = r.scrape;
      h += '<div class="sr-status ok">Content scraped: ' + s.text.length + ' text blocks</div>';
    }
    if (r.scrape) {
      h += '<div class="detail" id="detail-' + i + '">' + buildScrapeDetail(r.scrape, 'r' + i) + '</div>';
    }
    h += '</div>';
  });
  h += '</div>';
  el.innerHTML = h;
}

function renderSearchResults(data) {
  const el = document.getElementById('results');
  let h = '<div class="sr-list">';
  data.results.forEach((r, i) => {
    const sr = r.search_result;
    const hasError = !!r.error;
    h += '<div class="sr-card' + (hasError ? ' has-error' : '') + '" onclick="toggleDetail(' + i + ')">';
    h += '<div class="sr-title">' + escHtml(sr.title) + '</div>';
    h += '<div class="sr-url">' + escHtml(sr.url) + '</div>';
    if (sr.snippet) h += '<div class="sr-snippet">' + escHtml(sr.snippet) + '</div>';
    if (hasError) {
      h += '<div class="sr-status fail">Failed to scrape: ' + escHtml(r.error) + '</div>';
    } else {
      const s = r.scrape;
      h += '<div class="sr-status ok">Scraped: ' + s.text.length + ' text blocks, ' + s.links.length + ' links, ' + s.images.length + ' images</div>';
    }
    if (r.scrape) {
      h += '<div class="detail" id="detail-' + i + '">' + buildScrapeDetail(r.scrape, 'r' + i) + '</div>';
    }
    h += '</div>';
  });
  h += '</div>';
  el.innerHTML = h;
}

function toggleDetail(i) {
  const d = document.getElementById('detail-' + i);
  if (!d) return;
  const open = d.classList.toggle('open');
  if (open) switchTab('r' + i, 'metadata');
}

function buildScrapeDetail(data, prefix) {
  let h = '<div class="tabs">';
  h += '<div class="tab active" onclick="event.stopPropagation();switchTab(\\''+prefix+'\\',\\'metadata\\')">Metadata</div>';
  h += '<div class="tab" onclick="event.stopPropagation();switchTab(\\''+prefix+'\\',\\'text\\')">Text <span class="count">(' + data.text.length + ')</span></div>';
  h += '<div class="tab" onclick="event.stopPropagation();switchTab(\\''+prefix+'\\',\\'links\\')">Links <span class="count">(' + data.links.length + ')</span></div>';
  h += '<div class="tab" onclick="event.stopPropagation();switchTab(\\''+prefix+'\\',\\'images\\')">Images <span class="count">(' + data.images.length + ')</span></div>';
  h += '<div class="tab" onclick="event.stopPropagation();switchTab(\\''+prefix+'\\',\\'raw\\')">Raw JSON</div>';
  h += '</div>';

  const m = data.metadata;
  let meta = '<div class="meta-grid">';
  meta += mrow('URL', '<a href="'+escAttr(data.url)+'" target="_blank" onclick="event.stopPropagation()">'+escHtml(data.url)+'</a>');
  meta += mrow('Status', data.status_code);
  meta += mrow('Title', m.title || '\\u2014');
  meta += mrow('Description', m.description || '\\u2014');
  meta += mrow('Keywords', m.keywords || '\\u2014');
  if (m.og_tags) for (const [k,v] of Object.entries(m.og_tags)) meta += mrow('og:'+k, escHtml(v));
  meta += '</div>';

  let text = '';
  for (const b of data.text) text += '<div class="text-block"><span class="tag">'+b.tag+'</span>'+escHtml(b.text)+'</div>';

  let links = '';
  for (const l of data.links) links += '<div class="link-item"><a href="'+escAttr(l.href)+'" target="_blank" onclick="event.stopPropagation()">'+escHtml(l.href)+'</a>'+(l.text?'<div class="link-text">'+escHtml(l.text)+'</div>':'')+'</div>';

  let imgs = '';
  for (const img of data.images) imgs += '<div class="img-item"><a href="'+escAttr(img.src)+'" target="_blank" onclick="event.stopPropagation()">'+escHtml(img.src)+'</a>'+(img.alt?'<div class="link-text">'+escHtml(img.alt)+'</div>':'')+'</div>';

  h += '<div class="panel active" id="panel-'+prefix+'-metadata">' + meta + '</div>';
  h += '<div class="panel" id="panel-'+prefix+'-text">' + (text || '<em>No text found.</em>') + '</div>';
  h += '<div class="panel" id="panel-'+prefix+'-links">' + (links || '<em>No links found.</em>') + '</div>';
  h += '<div class="panel" id="panel-'+prefix+'-images">' + (imgs || '<em>No images found.</em>') + '</div>';
  h += '<div class="panel" id="panel-'+prefix+'-raw"><pre style="white-space:pre-wrap;font-size:.8rem;">' + escHtml(JSON.stringify(data, null, 2)) + '</pre></div>';
  return h;
}

function mrow(label, value) { return '<div class="meta-label">'+escHtml(label)+'</div><div class="meta-value">'+value+'</div>'; }

function switchTab(prefix, name) {
  const tabs = ['metadata','text','links','images','raw'];
  tabs.forEach(t => {
    const panel = document.getElementById('panel-' + prefix + '-' + t);
    if (panel) panel.classList.toggle('active', t === name);
  });
  event && event.currentTarget && event.currentTarget.parentElement &&
    event.currentTarget.parentElement.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.textContent.trim().toLowerCase().startsWith(name)));
}

function escHtml(s) { if (s == null) return ''; const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML; }
function escAttr(s) { return String(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }

document.getElementById('mainInput').addEventListener('keydown', e => { if (e.key === 'Enter') doAction(); });
</script>
</body>
</html>
"""
