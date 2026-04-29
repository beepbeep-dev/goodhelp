import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl, Field

from app.scraper import scrape_url
from app.searcher import search_web, search_pastes, deep_search

app = FastAPI(
    title="GoodHelp Web Scraper",
    description="Search, scrape, and deep-crawl the web via a clean API.",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- request models ----------

class ScrapeRequest(BaseModel):
    url: HttpUrl = Field(..., description="URL to scrape")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    num_results: int = Field(5, ge=1, le=50, description="Number of results")


class PasteSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Keywords to search paste sites")
    num_results: int = Field(10, ge=1, le=50, description="Number of results")


class DeepSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Deep search query")
    num_results: int = Field(5, ge=1, le=20, description="Top results to scrape")
    max_depth_links: int = Field(3, ge=0, le=10, description="Max links to follow from results")


# ---------- response models ----------

class ErrorDetail(BaseModel):
    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    uptime_seconds: float


class ScrapeResponse(BaseModel):
    ok: bool = True
    data: dict[str, Any]


class SearchResponse(BaseModel):
    ok: bool = True
    query: str
    result_count: int
    results: list[dict[str, Any]]


class DeepSearchResponse(BaseModel):
    ok: bool = True
    query: str
    results: list[dict[str, Any]]
    deep_results: list[dict[str, Any]]
    stats: dict[str, int]


# ---------- state ----------

_start_time = time.time()


# ---------- v1 API ----------

@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
async def health():
    return HealthResponse(
        version=app.version,
        uptime_seconds=round(time.time() - _start_time, 1),
    )


@app.post("/api/v1/scrape", response_model=ScrapeResponse, tags=["scrape"])
async def api_v1_scrape(req: ScrapeRequest):
    try:
        data = await scrape_url(str(req.url))
        return ScrapeResponse(data=data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/api/v1/search", tags=["search"])
async def api_v1_search(req: SearchRequest):
    results = await search_web(req.query, req.num_results)
    return {"ok": True, "query": req.query, "result_count": len(results), "results": results}


@app.post("/api/v1/search-and-scrape", response_model=SearchResponse, tags=["search"])
async def api_v1_search_and_scrape(req: SearchRequest):
    search_results = await search_web(req.query, req.num_results)
    scraped = []
    for sr in search_results:
        try:
            data = await scrape_url(sr["url"])
            scraped.append({"search_result": sr, "scrape": data, "error": None})
        except Exception as e:
            scraped.append({"search_result": sr, "scrape": None, "error": str(e)})
    return {"ok": True, "query": req.query, "result_count": len(scraped), "results": scraped}


@app.post("/api/v1/paste-search", response_model=SearchResponse, tags=["search"])
async def api_v1_paste_search(req: PasteSearchRequest):
    search_results = await search_pastes(req.query, req.num_results)
    scraped = []
    for sr in search_results:
        try:
            data = await scrape_url(sr["url"])
            scraped.append({"search_result": sr, "scrape": data, "error": None})
        except Exception as e:
            scraped.append({"search_result": sr, "scrape": None, "error": str(e)})
    return {"ok": True, "query": req.query, "result_count": len(scraped), "results": scraped}


@app.post("/api/v1/deep-search", response_model=DeepSearchResponse, tags=["search"])
async def api_v1_deep_search(req: DeepSearchRequest):
    data = await deep_search(req.query, req.num_results, req.max_depth_links)
    return {"ok": True, **data}


# ---------- backward-compat routes (no /v1/) ----------

@app.post("/api/scrape", tags=["legacy"], include_in_schema=False)
async def api_scrape(req: ScrapeRequest):
    try:
        return await scrape_url(str(req.url))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/api/search", tags=["legacy"], include_in_schema=False)
async def api_search(req: SearchRequest):
    results = await search_web(req.query, req.num_results)
    return {"query": req.query, "results": results}


@app.post("/api/search-and-scrape", tags=["legacy"], include_in_schema=False)
async def api_search_and_scrape(req: SearchRequest):
    search_results = await search_web(req.query, req.num_results)
    scraped = []
    for sr in search_results:
        try:
            data = await scrape_url(sr["url"])
            scraped.append({"search_result": sr, "scrape": data, "error": None})
        except Exception as e:
            scraped.append({"search_result": sr, "scrape": None, "error": str(e)})
    return {"query": req.query, "results": scraped}


@app.post("/api/paste-search", tags=["legacy"], include_in_schema=False)
async def api_paste_search(req: PasteSearchRequest):
    search_results = await search_pastes(req.query, req.num_results)
    scraped = []
    for sr in search_results:
        try:
            data = await scrape_url(sr["url"])
            scraped.append({"search_result": sr, "scrape": data, "error": None})
        except Exception as e:
            scraped.append({"search_result": sr, "scrape": None, "error": str(e)})
    return {"query": req.query, "results": scraped}


@app.post("/api/deep-search", tags=["legacy"], include_in_schema=False)
async def api_deep_search(req: DeepSearchRequest):
    return await deep_search(req.query, req.num_results, req.max_depth_links)


# ---------- UI ----------

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>GoodHelp Scraper</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  :root {
    --bg: #0a0e1a;
    --bg2: #111827;
    --card: rgba(30,41,59,.65);
    --card-border: rgba(56,189,248,.12);
    --accent: #38bdf8;
    --accent2: #818cf8;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --green: #34d399;
    --red: #fb7185;
    --purple: #c084fc;
    --glass: rgba(255,255,255,.04);
    --glow: 0 0 30px rgba(56,189,248,.08);
    --radius: .75rem;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Inter',system-ui,sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }

  /* animated gradient bg */
  body::before {
    content:''; position:fixed; inset:0; z-index:-1;
    background: radial-gradient(ellipse at 20% 0%, rgba(56,189,248,.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 100%, rgba(129,140,248,.06) 0%, transparent 50%);
  }

  .container { max-width:1100px; margin:0 auto; padding:2.5rem 1.25rem; }

  /* header */
  .header { text-align:center; margin-bottom:2rem; }
  .header h1 {
    font-size:2.2rem; font-weight:700; letter-spacing:-.02em;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  }
  .header p { color:var(--muted); font-size:.9rem; margin-top:.4rem; }
  .header .version { font-size:.7rem; color:var(--accent); opacity:.5; margin-top:.2rem; }

  /* mode toggle */
  .mode-toggle { display:flex; justify-content:center; gap:.5rem; margin-bottom:1.75rem; flex-wrap:wrap; }
  .mode-btn {
    padding:.55rem 1.3rem; border:1px solid var(--card-border); border-radius:2rem;
    background:var(--glass); color:var(--muted); cursor:pointer; font-size:.85rem;
    font-weight:500; transition: all .2s ease; backdrop-filter:blur(8px);
  }
  .mode-btn:hover { border-color:var(--accent); color:var(--text); }
  .mode-btn.active {
    color:var(--accent); border-color:var(--accent);
    background: rgba(56,189,248,.08);
    box-shadow: 0 0 20px rgba(56,189,248,.1);
  }

  /* search box */
  .search-box { display:flex; gap:.5rem; margin-bottom:1.75rem; }
  .search-box input {
    flex:1; padding:.85rem 1.15rem; border:1px solid var(--card-border); border-radius:var(--radius);
    background:var(--card); color:var(--text); font-size:1rem; outline:none;
    backdrop-filter:blur(12px); transition: border-color .2s, box-shadow .2s;
  }
  .search-box input:focus { border-color:var(--accent); box-shadow: 0 0 0 3px rgba(56,189,248,.1); }
  .search-box input::placeholder { color:var(--muted); }
  .search-box button {
    padding:.85rem 1.75rem; border:none; border-radius:var(--radius);
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color:#0f172a; font-weight:600; font-size:.95rem; cursor:pointer;
    white-space:nowrap; transition: opacity .15s, transform .1s;
  }
  .search-box button:hover { opacity:.9; transform:translateY(-1px); }
  .search-box button:active { transform:translateY(0); }
  .search-box button:disabled { opacity:.4; cursor:not-allowed; transform:none; }

  /* spinner */
  .spinner {
    display:none; text-align:center; padding:3rem; color:var(--muted); font-size:.9rem;
  }
  .spinner .dots { display:inline-flex; gap:.3rem; margin-bottom:.5rem; }
  .spinner .dot {
    width:8px; height:8px; border-radius:50%;
    background:var(--accent); animation: bounce .6s ease-in-out infinite alternate;
  }
  .spinner .dot:nth-child(2) { animation-delay:.15s; background:var(--accent2); }
  .spinner .dot:nth-child(3) { animation-delay:.3s; background:var(--purple); }
  @keyframes bounce { to { opacity:.3; transform:translateY(-6px); } }

  /* toast */
  .toast {
    position:fixed; bottom:1.5rem; right:1.5rem; padding:.85rem 1.25rem; border-radius:var(--radius);
    background:rgba(251,113,133,.15); border:1px solid var(--red); color:var(--red);
    font-size:.85rem; z-index:1000; backdrop-filter:blur(12px);
    animation: slideIn .3s ease-out; max-width:400px;
  }
  @keyframes slideIn { from { transform:translateX(100%); opacity:0; } to { transform:translateX(0); opacity:1; } }
  @keyframes fadeOut { to { opacity:0; transform:translateY(10px); } }

  /* result cards */
  .sr-list { margin-bottom:1.5rem; }
  .sr-card {
    background:var(--card); border-radius:var(--radius); padding:1rem 1.25rem;
    margin-bottom:.6rem; border-left:3px solid var(--accent); cursor:pointer;
    transition: all .2s ease; backdrop-filter:blur(8px);
    border:1px solid var(--card-border); border-left-width:3px;
    animation: fadeUp .3s ease-out both;
  }
  @keyframes fadeUp { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
  .sr-card:hover { border-left-color:var(--green); transform:translateY(-1px); box-shadow:var(--glow); }
  .sr-card.has-error { border-left-color:var(--red); }
  .sr-card.expanded { border-left-color:var(--green); box-shadow:var(--glow); }
  .sr-title { font-weight:600; margin-bottom:.25rem; font-size:.95rem; }
  .sr-url { color:var(--muted); font-size:.78rem; word-break:break-all; margin-bottom:.25rem; }
  .sr-url a { color:var(--accent); text-decoration:none; }
  .sr-url a:hover { text-decoration:underline; }
  .sr-snippet { font-size:.83rem; color:var(--muted); line-height:1.45; }
  .sr-status { font-size:.75rem; margin-top:.5rem; display:flex; align-items:center; gap:.4rem; }
  .sr-status.ok { color:var(--green); }
  .sr-status.fail { color:var(--red); }

  /* badges */
  .badge {
    font-size:.65rem; font-weight:600; padding:.2rem .55rem; border-radius:1rem;
    background:rgba(255,255,255,.06); text-transform:uppercase; letter-spacing:.04em;
  }

  /* stats banner */
  .stats-banner {
    background:var(--card); backdrop-filter:blur(12px); padding:.85rem 1.25rem;
    border-radius:var(--radius); margin-bottom:1.25rem; display:flex; gap:1.5rem;
    flex-wrap:wrap; font-size:.85rem; border:1px solid var(--card-border);
    animation: fadeUp .3s ease-out;
  }
  .stats-banner span { display:flex; align-items:center; gap:.3rem; }

  /* section headers */
  .section-header {
    font-size:.75rem; font-weight:600; text-transform:uppercase; letter-spacing:.06em;
    margin-bottom:.6rem; display:flex; align-items:center; gap:.5rem;
    padding-bottom:.4rem; border-bottom:1px solid var(--card-border);
  }

  /* detail panel */
  .detail { display:none; margin-top:.75rem; padding-top:.75rem; border-top:1px solid rgba(255,255,255,.06); }
  .detail.open { display:block; animation: fadeUp .2s ease-out; }
  .tabs { display:flex; gap:.25rem; margin-bottom:.75rem; flex-wrap:wrap; }
  .tab {
    padding:.4rem .75rem; border-radius:var(--radius) var(--radius) 0 0;
    background:var(--bg2); color:var(--muted); cursor:pointer; border:1px solid transparent;
    font-size:.82rem; transition: color .15s, border-color .15s;
  }
  .tab:hover { color:var(--text); }
  .tab.active { color:var(--accent); border-color:var(--accent); border-bottom-color:var(--bg2); }
  .panel {
    display:none; background:var(--bg2); border-radius:0 var(--radius) var(--radius) var(--radius);
    padding:1rem; max-height:50vh; overflow-y:auto; font-size:.85rem; line-height:1.5;
  }
  .panel.active { display:block; }
  .meta-grid { display:grid; grid-template-columns:130px 1fr; gap:.4rem; }
  .meta-label { color:var(--muted); font-size:.8rem; }
  .meta-value { word-break:break-all; }
  .text-block { margin-bottom:.5rem; }
  .text-block .tag {
    display:inline-block; background:rgba(56,189,248,.1); color:var(--accent);
    padding:.1rem .4rem; border-radius:.25rem; font-size:.7rem; margin-right:.4rem; font-weight:500;
  }
  .link-item, .img-item { padding:.4rem 0; border-bottom:1px solid rgba(255,255,255,.04); }
  .link-item a, .img-item a { color:var(--accent); text-decoration:none; word-break:break-all; }
  .link-item a:hover, .img-item a:hover { text-decoration:underline; }
  .link-text { color:var(--muted); font-size:.8rem; }
  .count { font-size:.72rem; color:var(--muted); margin-left:.15rem; }

  /* single result */
  .single-result { background:var(--card); border-radius:var(--radius); padding:1.25rem; backdrop-filter:blur(8px); border:1px solid var(--card-border); }

  /* result count */
  .result-count {
    text-align:center; font-size:.8rem; color:var(--muted); margin-bottom:1rem;
    animation: fadeUp .3s ease-out;
  }
  .result-count b { color:var(--accent); }

  /* copy button */
  .copy-btn {
    font-size:.7rem; color:var(--muted); cursor:pointer; padding:.2rem .5rem;
    border-radius:.25rem; border:1px solid var(--card-border); background:transparent;
    transition: all .15s;
  }
  .copy-btn:hover { color:var(--accent); border-color:var(--accent); }

  /* keyboard hint */
  .kbd { font-size:.7rem; color:var(--muted); text-align:center; margin-top:-.75rem; margin-bottom:1rem; opacity:.6; }
  kbd { background:var(--bg2); padding:.1rem .35rem; border-radius:.2rem; font-size:.7rem; border:1px solid var(--card-border); }

  /* scrollbar */
  ::-webkit-scrollbar { width:6px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:rgba(255,255,255,.1); border-radius:3px; }

  #results { display:none; }

  /* responsive */
  @media (max-width:640px) {
    .container { padding:1.5rem .75rem; }
    .header h1 { font-size:1.6rem; }
    .search-box { flex-direction:column; }
    .search-box button { width:100%; }
    .mode-toggle { gap:.35rem; }
    .mode-btn { padding:.45rem .9rem; font-size:.8rem; }
    .stats-banner { gap:.75rem; font-size:.8rem; }
    .meta-grid { grid-template-columns:1fr; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>GoodHelp Scraper</h1>
    <p>Search, scrape, and deep-crawl the web</p>
    <div class="version">v2.0 &middot; API docs at <a href="/api/docs" style="color:var(--accent);text-decoration:none">/api/docs</a></div>
  </div>

  <div class="mode-toggle">
    <div class="mode-btn active" onclick="setMode('search')" id="mode-search">Search &amp; Scrape</div>
    <div class="mode-btn" onclick="setMode('paste')" id="mode-paste">Cool Mode &#128526;</div>
    <div class="mode-btn" onclick="setMode('deep')" id="mode-deep">Deep Search &#128373;</div>
    <div class="mode-btn" onclick="setMode('url')" id="mode-url">Scrape URL</div>
  </div>

  <div class="search-box">
    <input type="text" id="mainInput" placeholder="What are you looking for?" autocomplete="off" spellcheck="false" />
    <button id="goBtn" onclick="doAction()">Search &amp; Scrape</button>
  </div>
  <div class="kbd">Press <kbd>Enter</kbd> to search</div>

  <div class="spinner" id="spinner"><div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div><div id="spinnerText">Working...</div></div>
  <div id="results"></div>
</div>

<script>
let currentMode = 'search';
const BASE = window.location.origin;

function setMode(mode) {
  currentMode = mode;
  ['search','paste','deep','url'].forEach(m => {
    document.getElementById('mode-' + m).classList.toggle('active', m === mode);
  });
  const input = document.getElementById('mainInput');
  const btn = document.getElementById('goBtn');
  const cfg = {
    search: { type:'text', placeholder:'What are you looking for?', btn:'Search & Scrape' },
    paste: { type:'text', placeholder:'Keywords to search pastes, Telegram, Discord...', btn:'Cool Search' },
    deep: { type:'text', placeholder:'Deep search \u2014 follows links to dig deeper...', btn:'Deep Search' },
    url: { type:'url', placeholder:'https://example.com', btn:'Scrape' },
  }[mode];
  input.type = cfg.type;
  input.placeholder = cfg.placeholder;
  btn.textContent = cfg.btn;
  document.getElementById('results').style.display = 'none';
  hideToast();
}

/* toast notifications */
let toastTimer;
function showToast(msg) {
  hideToast();
  const t = document.createElement('div');
  t.className = 'toast'; t.id = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  toastTimer = setTimeout(() => { t.style.animation = 'fadeOut .3s ease-in forwards'; setTimeout(hideToast, 300); }, 5000);
}
function hideToast() {
  clearTimeout(toastTimer);
  const t = document.getElementById('toast');
  if (t) t.remove();
}

async function doAction() {
  const val = document.getElementById('mainInput').value.trim();
  if (!val) return;
  if (currentMode === 'url') return doScrapeUrl(val);
  if (currentMode === 'paste') return doPasteSearch(val);
  if (currentMode === 'deep') return doDeepSearch(val);
  return doSearchScrape(val);
}

function startLoading(msg) {
  const btn = document.getElementById('goBtn');
  const spinner = document.getElementById('spinner');
  const results = document.getElementById('results');
  btn.disabled = true;
  spinner.style.display = 'block';
  document.getElementById('spinnerText').textContent = msg || 'Working...';
  results.style.display = 'none';
  hideToast();
}

function stopLoading() {
  document.getElementById('goBtn').disabled = false;
  document.getElementById('spinner').style.display = 'none';
}

async function apiCall(endpoint, body) {
  const res = await fetch(BASE + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { const e = await res.json(); msg = e.detail || e.error || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

async function doSearchScrape(query) {
  startLoading('Searching and scraping...');
  try {
    const data = await apiCall('/api/v1/search-and-scrape', { query, num_results: 5 });
    renderSearchResults(data);
    document.getElementById('results').style.display = 'block';
  } catch (e) { showToast(e.message); }
  finally { stopLoading(); }
}

async function doPasteSearch(query) {
  startLoading('Searching paste sites, Telegram, Discord...');
  try {
    const data = await apiCall('/api/v1/paste-search', { query, num_results: 10 });
    renderPasteResults(data);
    document.getElementById('results').style.display = 'block';
  } catch (e) { showToast(e.message); }
  finally { stopLoading(); }
}

async function doDeepSearch(query) {
  startLoading('Deep searching \u2014 scraping pages and following links...');
  try {
    const data = await apiCall('/api/v1/deep-search', { query, num_results: 5, max_depth_links: 3 });
    renderDeepResults(data);
    document.getElementById('results').style.display = 'block';
  } catch (e) { showToast(e.message); }
  finally { stopLoading(); }
}

async function doScrapeUrl(url) {
  startLoading('Scraping page...');
  try {
    const data = await apiCall('/api/v1/scrape', { url });
    const results = document.getElementById('results');
    results.innerHTML = '<div class="single-result">' + buildScrapeDetail(data.data, 'single') + '</div>';
    results.style.display = 'block';
    switchTab('single', 'metadata');
  } catch (e) { showToast(e.message); }
  finally { stopLoading(); }
}

/* deep search renderer */
function renderDeepResults(data) {
  const el = document.getElementById('results');
  const st = data.stats;
  let h = '<div class="stats-banner">';
  h += '<span style="color:var(--accent)">&#128269; Searched: <b>' + st.pages_searched + '</b></span>';
  h += '<span style="color:var(--green)">&#128196; Scraped: <b>' + st.pages_scraped + '</b></span>';
  h += '<span style="color:var(--purple)">&#128279; Followed: <b>' + st.links_followed + '</b></span>';
  h += '<span style="color:var(--muted)">Links found: <b>' + st.total_links_found + '</b></span>';
  h += '</div>';

  const total = data.results.length + (data.deep_results ? data.deep_results.length : 0);
  h += '<div class="result-count"><b>' + total + '</b> results across <b>2</b> depth levels</div>';

  if (data.results.length) {
    h += '<div class="section-header" style="color:var(--accent)"><span>&#9679;</span> Depth 0 &mdash; Direct Results</div>';
    h += '<div class="sr-list">';
    data.results.forEach((r, i) => { h += buildDeepCard(r, i, false); });
    h += '</div>';
  }
  if (data.deep_results && data.deep_results.length) {
    h += '<div class="section-header" style="color:var(--purple)"><span>&#128279;</span> Depth 1 &mdash; Followed Links</div>';
    h += '<div class="sr-list">';
    data.deep_results.forEach((r, i) => { h += buildDeepCard(r, 'd' + i, true); });
    h += '</div>';
  }
  if (!data.results.length && (!data.deep_results || !data.deep_results.length)) {
    h += '<div style="text-align:center;color:var(--muted);padding:3rem;">No results found.</div>';
  }
  el.innerHTML = h;
}

function buildDeepCard(r, idx, isDeep) {
  const sr = r.search_result;
  const hasError = !!r.error;
  const borderColor = isDeep ? 'var(--purple)' : 'var(--accent)';
  const delay = (typeof idx === 'number' ? idx : parseInt(String(idx).replace('d',''),10)) * 0.05;
  let c = '<div class="sr-card' + (hasError ? ' has-error' : '') + '" onclick="toggleDetail(\'' + idx + '\')" style="border-left-color:' + borderColor + ';animation-delay:' + delay + 's">';
  c += '<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem"><div class="sr-title">' + esc(sr.title) + '</div>';
  if (isDeep) c += '<span class="badge" style="color:var(--purple);border:1px solid rgba(192,132,252,.2)">depth 1</span>';
  c += '</div>';
  c += '<div class="sr-url"><a href="' + escA(sr.url) + '" target="_blank" onclick="event.stopPropagation()">' + esc(sr.url) + '</a></div>';
  if (sr.snippet) c += '<div class="sr-snippet">' + esc(sr.snippet) + '</div>';
  if (hasError) {
    c += '<div class="sr-status fail">&#10007; ' + esc(r.error) + '</div>';
  } else if (r.scrape) {
    const s = r.scrape;
    c += '<div class="sr-status ok">&#10003; ' + s.text.length + ' text blocks &middot; ' + s.links.length + ' links &middot; ' + s.images.length + ' images' + (s.word_count ? ' &middot; ~' + s.word_count + ' words' : '') + '</div>';
  }
  if (r.scrape) c += '<div class="detail" id="detail-' + idx + '">' + buildScrapeDetail(r.scrape, 'r' + idx) + '</div>';
  c += '</div>';
  return c;
}

/* paste results */
const SOURCE_COLORS = { telegram:'#26A5E4', discord:'#5865F2' };
function badgeColor(src) { return SOURCE_COLORS[src] || '#a78bfa'; }

function renderPasteResults(data) {
  const el = document.getElementById('results');
  if (!data.results.length) {
    el.innerHTML = '<div style="text-align:center;color:var(--muted);padding:3rem;">No results found. Try different keywords.</div>';
    return;
  }
  let h = '<div class="result-count"><b>' + data.results.length + '</b> results from paste sites &amp; messaging platforms</div>';
  h += '<div class="sr-list">';
  data.results.forEach((r, i) => {
    const sr = r.search_result;
    const hasError = !!r.error;
    const bc = badgeColor(sr.source);
    h += '<div class="sr-card' + (hasError ? ' has-error' : '') + '" onclick="toggleDetail(' + i + ')" style="border-left-color:' + bc + ';animation-delay:' + (i*0.05) + 's">';
    h += '<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem"><div class="sr-title">' + esc(sr.title) + '</div>';
    h += '<span class="badge" style="color:' + bc + ';border:1px solid ' + bc + '33">' + esc(sr.source) + '</span></div>';
    h += '<div class="sr-url"><a href="' + escA(sr.url) + '" target="_blank" onclick="event.stopPropagation()">' + esc(sr.url) + '</a></div>';
    if (sr.snippet) h += '<div class="sr-snippet">' + esc(sr.snippet) + '</div>';
    if (hasError) {
      h += '<div class="sr-status fail">&#10007; ' + esc(r.error) + '</div>';
    } else if (r.scrape) {
      const s = r.scrape;
      h += '<div class="sr-status ok">&#10003; ' + s.text.length + ' text blocks' + (s.word_count ? ' &middot; ~' + s.word_count + ' words' : '') + '</div>';
    }
    if (r.scrape) h += '<div class="detail" id="detail-' + i + '">' + buildScrapeDetail(r.scrape, 'r' + i) + '</div>';
    h += '</div>';
  });
  h += '</div>';
  el.innerHTML = h;
}

/* search results */
function renderSearchResults(data) {
  const el = document.getElementById('results');
  let h = '<div class="result-count"><b>' + data.results.length + '</b> results found and scraped</div>';
  h += '<div class="sr-list">';
  data.results.forEach((r, i) => {
    const sr = r.search_result;
    const hasError = !!r.error;
    h += '<div class="sr-card' + (hasError ? ' has-error' : '') + '" onclick="toggleDetail(' + i + ')" style="animation-delay:' + (i*0.05) + 's">';
    h += '<div class="sr-title">' + esc(sr.title) + '</div>';
    h += '<div class="sr-url"><a href="' + escA(sr.url) + '" target="_blank" onclick="event.stopPropagation()">' + esc(sr.url) + '</a></div>';
    if (sr.snippet) h += '<div class="sr-snippet">' + esc(sr.snippet) + '</div>';
    if (hasError) {
      h += '<div class="sr-status fail">&#10007; ' + esc(r.error) + '</div>';
    } else if (r.scrape) {
      const s = r.scrape;
      h += '<div class="sr-status ok">&#10003; ' + s.text.length + ' text blocks &middot; ' + s.links.length + ' links &middot; ' + s.images.length + ' images' + (s.word_count ? ' &middot; ~' + s.word_count + ' words' : '') + '</div>';
    }
    if (r.scrape) h += '<div class="detail" id="detail-' + i + '">' + buildScrapeDetail(r.scrape, 'r' + i) + '</div>';
    h += '</div>';
  });
  h += '</div>';
  el.innerHTML = h;
}

function toggleDetail(i) {
  const d = document.getElementById('detail-' + i);
  if (!d) return;
  const card = d.parentElement;
  const open = d.classList.toggle('open');
  card.classList.toggle('expanded', open);
  if (open) switchTab('r' + i, 'metadata');
}

function buildScrapeDetail(data, prefix) {
  let h = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem">';
  h += '<div class="tabs">';
  h += '<div class="tab active" onclick="event.stopPropagation();switchTab(\''+prefix+'\',\'metadata\')">Metadata</div>';
  h += '<div class="tab" onclick="event.stopPropagation();switchTab(\''+prefix+'\',\'text\')">Text <span class="count">(' + data.text.length + ')</span></div>';
  h += '<div class="tab" onclick="event.stopPropagation();switchTab(\''+prefix+'\',\'links\')">Links <span class="count">(' + data.links.length + ')</span></div>';
  h += '<div class="tab" onclick="event.stopPropagation();switchTab(\''+prefix+'\',\'images\')">Images <span class="count">(' + data.images.length + ')</span></div>';
  h += '<div class="tab" onclick="event.stopPropagation();switchTab(\''+prefix+'\',\'raw\')">JSON</div>';
  h += '</div>';
  h += '<button class="copy-btn" onclick="event.stopPropagation();copyJSON(this,' + esc(JSON.stringify(JSON.stringify(data))) + ')">Copy JSON</button>';
  h += '</div>';

  const m = data.metadata;
  let meta = '<div class="meta-grid">';
  meta += mrow('URL', '<a href="'+escA(data.url)+'" target="_blank" onclick="event.stopPropagation()">'+esc(data.url)+'</a>');
  meta += mrow('Status', data.status_code);
  if (data.content_type) meta += mrow('Content-Type', esc(data.content_type));
  meta += mrow('Title', m.title || '\u2014');
  meta += mrow('Description', m.description || '\u2014');
  meta += mrow('Keywords', m.keywords || '\u2014');
  if (m.lang) meta += mrow('Language', esc(m.lang));
  if (m.favicon) meta += mrow('Favicon', '<img src="'+escA(m.favicon)+'" style="height:16px;vertical-align:middle"> ' + esc(m.favicon));
  if (m.og_tags) for (const [k,v] of Object.entries(m.og_tags)) meta += mrow('og:'+k, esc(v));
  if (data.word_count) meta += mrow('Word Count', '~' + data.word_count);
  meta += '</div>';

  let text = '';
  for (const b of data.text) text += '<div class="text-block"><span class="tag">'+b.tag+'</span>'+esc(b.text)+'</div>';

  let links = '';
  for (const l of data.links) links += '<div class="link-item"><a href="'+escA(l.href)+'" target="_blank" onclick="event.stopPropagation()">'+esc(l.href)+'</a>'+(l.text?'<div class="link-text">'+esc(l.text)+'</div>':'')+'</div>';

  let imgs = '';
  for (const img of data.images) imgs += '<div class="img-item"><a href="'+escA(img.src)+'" target="_blank" onclick="event.stopPropagation()">'+esc(img.src)+'</a>'+(img.alt?'<div class="link-text">'+esc(img.alt)+'</div>':'')+'</div>';

  h += '<div class="panel active" id="panel-'+prefix+'-metadata">' + meta + '</div>';
  h += '<div class="panel" id="panel-'+prefix+'-text">' + (text || '<em style="color:var(--muted)">No text extracted.</em>') + '</div>';
  h += '<div class="panel" id="panel-'+prefix+'-links">' + (links || '<em style="color:var(--muted)">No links found.</em>') + '</div>';
  h += '<div class="panel" id="panel-'+prefix+'-images">' + (imgs || '<em style="color:var(--muted)">No images found.</em>') + '</div>';
  h += '<div class="panel" id="panel-'+prefix+'-raw"><pre style="white-space:pre-wrap;font-size:.8rem;color:var(--muted)">' + esc(JSON.stringify(data, null, 2)) + '</pre></div>';
  return h;
}

function mrow(label, value) { return '<div class="meta-label">'+esc(label)+'</div><div class="meta-value">'+value+'</div>'; }

function switchTab(prefix, name) {
  const tabs = ['metadata','text','links','images','raw'];
  tabs.forEach(t => {
    const panel = document.getElementById('panel-' + prefix + '-' + t);
    if (panel) panel.classList.toggle('active', t === name);
  });
  if (event && event.currentTarget && event.currentTarget.parentElement) {
    event.currentTarget.parentElement.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.textContent.trim().toLowerCase().startsWith(name)));
  }
}

function copyJSON(btn, jsonStr) {
  navigator.clipboard.writeText(jsonStr).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy JSON'; }, 1500);
  });
}

function esc(s) { if (s == null) return ''; const d = document.createElement('div'); d.textContent = String(s); return d.innerHTML; }
function escA(s) { return String(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }

document.getElementById('mainInput').addEventListener('keydown', e => { if (e.key === 'Enter') doAction(); });
</script>
</body>
</html>"""
