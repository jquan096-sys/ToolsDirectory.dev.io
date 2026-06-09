
"""
agent_update.py  —  FULL AUTONOMOUS VERSION
============================================
Site: https://jquan096-sys.github.io/ToolsDirectory.dev.io/

What it does every day (via GitHub Actions cron):
  1. Fetches latest AI news from HackerNews, Dev.to, Product Hunt (all free)
  2. Uses Gemini 2.0 Flash to summarize & categorize each item (free tier)
  3. Rewrites data/news.json, data/tools_new.json, data/meta.json
  4. AUTO-PATCHES index.html to inject a fresh <script> block with today's tools
  5. GitHub Actions commits & pushes everything — site updates itself daily

Self-healing features:
  - Tries 3 Gemini models in order, uses first working one
  - Gracefully skips enrichment if API key missing/invalid
  - Never crashes on bad JSON or network errors
  - Idempotent: safe to run multiple times per day
"""

import os, json, datetime, urllib.request, urllib.parse, re, shutil

# ── CONFIG ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODELS   = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]
MAX_NEWS        = 12    # latest news cards shown on site
MAX_HISTORY     = 60    # rolling history kept in tools_new.json
OUTPUT_DIR      = "data"
NEWS_FILE       = f"{OUTPUT_DIR}/news.json"
TOOLS_FILE      = f"{OUTPUT_DIR}/tools_new.json"
META_FILE       = f"{OUTPUT_DIR}/meta.json"
INDEX_FILE      = "index.html"
TODAY           = datetime.date.today().isoformat()
NOW_UTC         = datetime.datetime.utcnow().isoformat() + "Z"

AI_KEYWORDS = [
    "AI","artificial intelligence","LLM","GPT","Claude","Gemini",
    "machine learning","automation","agent","chatbot","copilot",
    "generative","openai","anthropic","mistral","llama","deepseek",
    "hugging face","stable diffusion","midjourney","runway","cursor"
]

CATEGORIES = ["Writing","Coding","Automation","Design","Video",
              "Marketing","Productivity","Search","Research","Other"]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def fetch_json(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"ToolsDirectoryBot/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  [WARN] fetch failed: {url[:80]} — {e}")
        return None

def is_ai(text):
    t = text.lower()
    return any(k.lower() in t for k in AI_KEYWORDS)

def clip(text, n=280):
    s = str(text or "").replace("\n"," ").strip()
    return s[:n] + ("…" if len(s)>n else "")

def load_json(path):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except: return []

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ {path}  ({len(data) if isinstance(data,list) else '—'} items)")

# ── DATA SOURCES ──────────────────────────────────────────────────────────────
def fetch_hackernews():
    print("📡 HackerNews…")
    cutoff = int(datetime.datetime.now().timestamp()) - 86400*3
    url = f"https://hn.algolia.com/api/v1/search?query=AI+tools&tags=story&numericFilters=created_at_i>{cutoff}&hitsPerPage=30"
    data = fetch_json(url) or {}
    items = []
    for h in data.get("hits", []):
        t = h.get("title","")
        if not is_ai(t): continue
        items.append({"id":h.get("objectID",""), "title":t,
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "source":"HackerNews","points":h.get("points",0),
            "date":TODAY,"summary":clip(t),"category":"Other","tags":["AI","HackerNews"]})
    print(f"  → {len(items)}")
    return items

def fetch_devto():
    print("📡 Dev.to…")
    data = fetch_json("https://dev.to/api/articles?tag=ai&per_page=20&top=3")
    if not isinstance(data, list): return []
    items = []
    for a in data:
        t = a.get("title","")
        if not is_ai(t): continue
        items.append({"id":str(a.get("id","")), "title":t,
            "url":a.get("url",""), "source":"Dev.to",
            "points":a.get("public_reactions_count",0),
            "date":TODAY,"summary":clip(a.get("description",t)),
            "category":"Other","tags":a.get("tag_list",["AI"])})
    print(f"  → {len(items)}")
    return items

def fetch_producthunt():
    print("📡 Product Hunt RSS…")
    rss = "https://www.producthunt.com/feed"
    url = f"https://api.rss2json.com/v1/api.json?rss_url={urllib.parse.quote(rss)}&count=20"
    data = fetch_json(url) or {}
    if data.get("status") != "ok": return []
    items = []
    for e in data.get("items",[]):
        t = e.get("title","")
        if not is_ai(t + e.get("description","")): continue
        items.append({"id":e.get("guid",e.get("link","")), "title":t,
            "url":e.get("link",""), "source":"Product Hunt","points":0,
            "date":TODAY,"summary":clip(e.get("description","")),
            "category":"Other","tags":["AI","Product Hunt"]})
    print(f"  → {len(items)}")
    return items

# ── GEMINI ENRICHMENT ─────────────────────────────────────────────────────────
def find_gemini_model():
    """Test each model, return the first one that responds."""
    if not GEMINI_API_KEY:
        return None
    for model in GEMINI_MODELS:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={GEMINI_API_KEY}")
        payload = json.dumps({"contents":[{"parts":[{"text":"Say OK"}]}],
                              "generationConfig":{"maxOutputTokens":5}}).encode()
        try:
            req = urllib.request.Request(url, data=payload,
                headers={"Content-Type":"application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10): pass
            print(f"  ✅ Gemini model: {model}")
            return model
        except Exception as e:
            print(f"  [INFO] {model} unavailable: {e}")
    return None

def enrich(items, model):
    if not model:
        print("⚠️  No Gemini model — skipping enrichment")
        return items
    cats = ", ".join(CATEGORIES)
    url  = (f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={GEMINI_API_KEY}")
    print(f"✨ Enriching {len(items)} items with {model}…")
    for item in items:
        prompt = (f"Title: {item['title']}\nSummary: {item['summary']}\n\n"
                  f"1. Write a 1-sentence description (max 120 chars) for an AI tools directory.\n"
                  f"2. Pick the best category from: {cats}\n\n"
                  f"Reply ONLY as valid JSON (no markdown):\n"
                  f"{{\"summary\":\"...\",\"category\":\"...\"}}")
        payload = json.dumps({"contents":[{"parts":[{"text":prompt}]}],
                              "generationConfig":{"temperature":0.2,"maxOutputTokens":150}}).encode()
        try:
            req = urllib.request.Request(url, data=payload,
                headers={"Content-Type":"application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=20) as r:
                result = json.loads(r.read().decode())
            text = (result["candidates"][0]["content"]["parts"][0]["text"]
                    .strip().replace("```json","").replace("```","").strip())
            enriched = json.loads(text)
            item["summary"]  = enriched.get("summary",  item["summary"])
            item["category"] = enriched.get("category", item["category"])
            print(f"  ✔ [{item['category']}] {item['title'][:55]}")
        except Exception as e:
            print(f"  [WARN] enrich fail '{item['title'][:45]}': {e}")
    return items

# ── AUTO-PATCH index.html ─────────────────────────────────────────────────────
def patch_index_html(news_items):
    """
    Inject a self-contained <script> block into index.html that:
    - Renders the latest news cards directly from the embedded JSON
    - No external fetch needed → works even before data/ folder is served
    - Wrapped in AUTO_NEWS markers so each run replaces the previous block
    """
    if not os.path.exists(INDEX_FILE):
        print(f"  [SKIP] {INDEX_FILE} not found — skipping HTML patch")
        return

    # Build compact news data (title, url, source, category, date, summary)
    compact = [{"t":i["title"],"u":i["url"],"s":i["source"],
                "c":i["category"],"d":i["date"],"m":i["summary"]}
               for i in news_items[:MAX_NEWS]]
    data_js = json.dumps(compact, ensure_ascii=False)

    injected = f"""
    <!-- AUTO_NEWS_START — regenerated {TODAY} by agent_update.py — do not edit -->
    <script>
    (function(){{
      var NEWS={data_js};
      var SRC_COLOR={{"HackerNews":"#ff6600","Dev.to":"#3b49df","Product Hunt":"#da552f"}};
      function esc(s){{return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}}
      function render(){{
        var el=document.getElementById("ai-news");
        if(!el)return;
        var cards=NEWS.map(function(n){{
          var clr=SRC_COLOR[n.s]||"#888";
          return '<a class="news-card" href="'+esc(n.u)+'" target="_blank" rel="noopener" style="display:flex;flex-direction:column;gap:6px;padding:16px;border:1px solid var(--border-color,#e5e7eb);border-radius:12px;background:var(--bg-card,#fff);text-decoration:none;color:inherit;transition:box-shadow .18s,transform .18s;" onmouseover="this.style.transform=\'translateY(-2px)\';this.style.boxShadow=\'0 6px 24px rgba(0,0,0,.1)\'" onmouseout="this.style.transform=\'\';this.style.boxShadow=\'\'">'
            +'<span style="display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;color:#fff;background:'+clr+';width:fit-content">'+esc(n.s)+'</span>'
            +'<span style="font-size:11px;font-weight:700;color:#6366f1;text-transform:uppercase;letter-spacing:.05em">'+esc(n.c)+'</span>'
            +'<strong style="font-size:14px;line-height:1.35;color:var(--text-primary,#1a1a2e)">'+esc(n.t)+'</strong>'
            +'<p style="font-size:12px;color:var(--text-secondary,#5f6368);margin:0;line-height:1.45">'+esc(n.m)+'</p>'
            +'<span style="font-size:11px;color:var(--text-muted,#80868b);margin-top:auto">'+esc(n.d)+'</span>'
            +'</a>';
        }}).join("");
        el.innerHTML='<p style="font-size:12px;color:var(--text-muted,#80868b);margin-bottom:12px">🔄 Updated: <strong>{TODAY}</strong></p>'
          +'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px">'+cards+'</div>';
      }}
      if(document.readyState==="loading"){{document.addEventListener("DOMContentLoaded",render);}}else{{render();}}
    }})();
    </script>
    <!-- AUTO_NEWS_END -->"""

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Make a backup just in case
    shutil.copy(INDEX_FILE, INDEX_FILE + ".bak")

    # Replace existing block if present, else insert before </body>
    pattern = r"<!-- AUTO_NEWS_START.*?AUTO_NEWS_END -->"
    if re.search(pattern, html, re.DOTALL):
        html = re.sub(pattern, injected.strip(), html, flags=re.DOTALL)
        print(f"  🔄 Replaced existing AUTO_NEWS block in {INDEX_FILE}")
    elif "</body>" in html:
        html = html.replace("</body>", injected + "\n</body>")
        print(f"  ➕ Injected AUTO_NEWS block into {INDEX_FILE}")
    else:
        print(f"  [WARN] Could not find </body> tag in {INDEX_FILE}")
        return

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ {INDEX_FILE} patched with {len(compact)} news items")

# ── MERGE HELPERS ─────────────────────────────────────────────────────────────
def merge(existing, new_items, max_keep):
    seen_ids  = {i["id"]  for i in existing}
    seen_urls = {i["url"] for i in existing}
    merged = list(existing)
    for item in new_items:
        if item["id"] not in seen_ids and item["url"] not in seen_urls:
            merged.append(item)
            seen_ids.add(item["id"])
            seen_urls.add(item["url"])
    merged.sort(key=lambda x: x.get("date",""), reverse=True)
    return merged[:max_keep]

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*58}")
    print(f"  ToolsDirectory Autonomous Agent  —  {TODAY}")
    print(f"{'='*58}\n")

    # 1. Collect
    raw = fetch_hackernews() + fetch_devto() + fetch_producthunt()
    print(f"\n📦 Raw collected: {len(raw)}")
    if not raw:
        print("⚠️  Nothing collected — stopping.")
        return

    # 2. Dedup within batch
    seen, unique = set(), []
    for item in raw:
        k = item["url"] or item["title"]
        if k not in seen:
            seen.add(k)
            unique.append(item)

    # 3. Enrich with Gemini (self-healing model selection)
    print("\n🔍 Finding working Gemini model…")
    model = find_gemini_model()
    unique = enrich(unique, model)

    # 4. Latest slice for news feed
    latest = unique[:MAX_NEWS]

    # 5. Merge with history
    existing_news  = load_json(NEWS_FILE)
    existing_tools = load_json(TOOLS_FILE)
    merged_news    = merge(existing_news,  latest, MAX_NEWS * 5)
    merged_tools   = merge(existing_tools, unique, MAX_HISTORY)

    # 6. Save JSON files
    print()
    save_json(NEWS_FILE,  merged_news)
    save_json(TOOLS_FILE, merged_tools)
    save_json(META_FILE, {
        "last_updated": NOW_UTC,
        "date":         TODAY,
        "total_news":   len(merged_news),
        "total_tools":  len(merged_tools),
        "ai_engine":    f"Gemini {model}" if model else "none (key missing)",
        "sources":      ["HackerNews","Dev.to","Product Hunt"],
        "items_today":  len(unique),
    })

    # 7. AUTO-PATCH index.html  ← self-updating website
    print()
    print("🌐 Patching index.html…")
    patch_index_html(latest)

    print(f"\n🎉 Done! {len(unique)} items processed, site updated.\n")

if __name__ == "__main__":
    main()
PYEOF
