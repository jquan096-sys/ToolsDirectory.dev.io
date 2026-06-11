"""
agent_update.py
===============
Auto-update agent for ToolsDirectory.dev.io
Fetches AI tool news, enriches with Gemini, writes data/news.json + data/meta.json
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.parse

# ── CONFIG ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-1.5-flash"
MAX_ITEMS      = 10
OUTPUT_DIR     = "data"
NEWS_FILE      = f"{OUTPUT_DIR}/news.json"
TOOLS_FILE     = f"{OUTPUT_DIR}/tools_new.json"
META_FILE      = f"{OUTPUT_DIR}/meta.json"
TODAY          = datetime.date.today().isoformat()

AI_KEYWORDS = [
    "AI", "artificial intelligence", "LLM", "GPT", "Claude", "Gemini",
    "machine learning", "automation", "agent", "chatbot", "copilot",
    "generative", "openai", "anthropic", "mistral", "llama", "deepseek",
    "neural", "transformer", "diffusion", "stable diffusion", "midjourney",
]

CATEGORIES = [
    "Writing", "Coding", "Automation", "Design", "Video",
    "Marketing", "Productivity", "Search", "Research", "Other",
]


# ── HELPERS ───────────────────────────────────────────────────────────────────
def fetch_json(url, timeout=15):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ToolsDirectoryBot/2.0 (+https://github.com/jquan096-sys)",
                "Accept": "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except Exception as e:
        print(f"  [WARN] fetch_json failed for {url[:80]}: {e}")
        return None


def is_ai_related(text):
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in AI_KEYWORDS)


def clean_text(text, max_len=300):
    if not text:
        return ""
    text = " ".join(text.split())  # collapse whitespace
    return text[:max_len] + ("..." if len(text) > max_len else "")


def safe_id(val):
    return str(val or "").strip()[:120]


# ── DATA SOURCES ──────────────────────────────────────────────────────────────
def fetch_hackernews():
    print("[SOURCE] HackerNews Algolia API")
    items = []
    cutoff = int(datetime.datetime.now().timestamp()) - 86400 * 3
    url = (
        "https://hn.algolia.com/api/v1/search"
        f"?query=AI+tools&tags=story&numericFilters=created_at_i>{cutoff}&hitsPerPage=30"
    )
    data = fetch_json(url)
    if not data:
        print("  [SKIP] HackerNews returned no data")
        return items
    for hit in data.get("hits", []):
        title = hit.get("title", "")
        if not is_ai_related(title):
            continue
        items.append({
            "id":       safe_id(hit.get("objectID")),
            "title":    title,
            "url":      hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "source":   "HackerNews",
            "points":   int(hit.get("points") or 0),
            "date":     TODAY,
            "summary":  clean_text(title),
            "category": "Other",
            "tags":     ["AI", "HackerNews"],
        })
    print(f"  -> {len(items)} AI items from HackerNews")
    return items


def fetch_devto():
    print("[SOURCE] Dev.to API")
    items = []
    url = "https://dev.to/api/articles?tag=ai&per_page=20&top=3"
    data = fetch_json(url)
    if not isinstance(data, list):
        print("  [SKIP] Dev.to returned no list")
        return items
    for art in data:
        title = art.get("title", "")
        if not is_ai_related(title + " " + art.get("description", "")):
            continue
        items.append({
            "id":       safe_id(art.get("id")),
            "title":    title,
            "url":      art.get("url", ""),
            "source":   "Dev.to",
            "points":   int(art.get("public_reactions_count") or 0),
            "date":     TODAY,
            "summary":  clean_text(art.get("description", title)),
            "category": "Other",
            "tags":     art.get("tag_list") or ["AI"],
        })
    print(f"  -> {len(items)} AI items from Dev.to")
    return items


def fetch_producthunt():
    print("[SOURCE] Product Hunt RSS via rss2json")
    items = []
    rss_url = "https://www.producthunt.com/feed"
    api_url = (
        "https://api.rss2json.com/v1/api.json"
        f"?rss_url={urllib.parse.quote(rss_url)}&count=20"
    )
    data = fetch_json(api_url)
    if not data or data.get("status") != "ok":
        print(f"  [SKIP] rss2json status: {data.get('status') if data else 'no response'}")
        return items
    for entry in data.get("items", []):
        title = entry.get("title", "")
        desc  = entry.get("description", "")
        if not is_ai_related(title + " " + desc):
            continue
        items.append({
            "id":       safe_id(entry.get("guid") or entry.get("link")),
            "title":    title,
            "url":      entry.get("link", ""),
            "source":   "Product Hunt",
            "points":   0,
            "date":     TODAY,
            "summary":  clean_text(desc),
            "category": "Other",
            "tags":     ["AI", "Product Hunt"],
        })
    print(f"  -> {len(items)} AI items from Product Hunt")
    return items


# ── GEMINI ENRICHMENT ─────────────────────────────────────────────────────────
def enrich_with_gemini(items):
    if not GEMINI_API_KEY:
        print("[SKIP] GEMINI_API_KEY not set - skipping enrichment")
        return items

    print(f"[GEMINI] Enriching {len(items)} items with {GEMINI_MODEL}...")
    cats_str = ", ".join(CATEGORIES)
    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    for i, item in enumerate(items):
        prompt = (
            f"Title: {item['title']}\n"
            f"Summary: {item['summary']}\n\n"
            f"1. Write a 1-sentence description (max 120 chars) for an AI tools directory.\n"
            f"2. Pick the best category from: {cats_str}\n\n"
            f"Reply ONLY as valid JSON, no markdown fences:\n"
            f"{{\"summary\": \"...\", \"category\": \"...\"}}"
        )
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 150},
        }).encode("utf-8")
        try:
            req = urllib.request.Request(
                api_url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            text = (
                result["candidates"][0]["content"]["parts"][0]["text"]
                .strip()
                .lstrip("```json").lstrip("```").rstrip("```").strip()
            )
            enriched = json.loads(text)
            item["summary"]  = enriched.get("summary",  item["summary"])[:200]
            item["category"] = enriched.get("category", item["category"])
            print(f"  [{i+1}/{len(items)}] [{item['category']}] {item['title'][:60]}")
        except Exception as e:
            print(f"  [WARN] Gemini failed for item {i+1}: {e}")

    print(f"[GEMINI] Done enriching {len(items)} items")
    return items


# ── DEDUP + MERGE ─────────────────────────────────────────────────────────────
def load_existing(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def merge_and_dedup(existing, new_items):
    seen_ids  = {item.get("id", "")  for item in existing if item.get("id")}
    seen_urls = {item.get("url", "") for item in existing if item.get("url")}
    merged = list(existing)
    added = 0
    for item in new_items:
        uid = item.get("id", "")
        url = item.get("url", "")
        if uid and uid in seen_ids:
            continue
        if url and url in seen_urls:
            continue
        merged.append(item)
        seen_ids.add(uid)
        seen_urls.add(url)
        added += 1
    merged.sort(key=lambda x: x.get("date", ""), reverse=True)
    print(f"  -> Added {added} new items, total {len(merged)} (capped at {MAX_ITEMS * 5})")
    return merged[:MAX_ITEMS * 5]


# ── WRITE JSON ────────────────────────────────────────────────────────────────
def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [SAVED] {filepath}  ({len(data)} items)")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"  ToolsDirectory Agent  -  {TODAY}")
    print(f"  Gemini key: {'SET' if GEMINI_API_KEY else 'NOT SET (enrichment skipped)'}")
    print("=" * 60)

    # 1. Collect
    raw = []
    raw += fetch_hackernews()
    raw += fetch_devto()
    raw += fetch_producthunt()
    print(f"\n[COLLECT] Total raw items: {len(raw)}")

    if not raw:
        print("[WARN] No items collected. Writing empty state and exiting.")
        # Still write meta so the site knows the agent ran
        meta = {
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
            "total_news": 0,
            "total_tools": 0,
            "ai_engine": f"Gemini {GEMINI_MODEL}" if GEMINI_API_KEY else "none",
            "sources": ["HackerNews", "Dev.to", "Product Hunt"],
            "status": "no_items_collected",
        }
        save_json(META_FILE, meta)
        sys.exit(0)  # exit 0 so GitHub Actions doesn't mark as failed

    # 2. Deduplicate within batch
    seen, unique = set(), []
    for item in raw:
        key = item.get("url") or item.get("title") or ""
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    print(f"[DEDUP] {len(unique)} unique items after dedup")

    # 3. Enrich with Gemini
    unique = enrich_with_gemini(unique)

    # 4. Merge with existing
    latest = unique[:MAX_ITEMS]
    existing_news  = load_existing(NEWS_FILE)
    existing_tools = load_existing(TOOLS_FILE)
    merged_news    = merge_and_dedup(existing_news,  latest)
    merged_tools   = merge_and_dedup(existing_tools, unique)

    # 5. Save files
    print()
    save_json(NEWS_FILE,  merged_news)
    save_json(TOOLS_FILE, merged_tools)

    # 6. Meta file
    meta = {
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "total_news":   len(merged_news),
        "total_tools":  len(merged_tools),
        "ai_engine":    f"Gemini {GEMINI_MODEL}" if GEMINI_API_KEY else "none",
        "sources":      ["HackerNews", "Dev.to", "Product Hunt"],
        "status":       "ok",
    }
    save_json(META_FILE, meta)

    print(f"\n[DONE] All files written to /{OUTPUT_DIR}/")
    sys.exit(0)


if __name__ == "__main__":
    main()
