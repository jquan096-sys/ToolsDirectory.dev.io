"""
agent_update.py
===============
Auto-update agent for https://jquan096-sys.github.io/ToolsDirectory.dev.io/

What it does:
  1. Fetches latest AI tool news from free APIs (HackerNews, Product Hunt RSS, Dev.to)
  2. Uses Google Gemini API (gemini-1.5-flash) to summarize + categorize each item
  3. Writes output to  data/news.json  and  data/tools_new.json
  4. GitHub Actions commits + pushes the updated JSON files automatically

Free APIs used (no key required):
  - HackerNews Algolia API  → algolia.hn/api/v1/search
  - Dev.to API              → dev.to/api/articles
  - Product Hunt RSS        → producthunt.com/feed  (via rss2json)

AI enrichment (add GEMINI_API_KEY secret in GitHub repo settings):
  - Google Gemini 1.5 Flash → FREE tier: 1,500 req/day, 1M tokens/min
  - Get your free key at: https://aistudio.google.com/apikey
"""

import os
import json
import datetime
import urllib.request
import urllib.parse

# ── CONFIG ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")   # Set in GitHub Secrets
GEMINI_MODEL   = "gemini-1.5-flash"                # Free tier model
MAX_ITEMS      = 10    # how many news/tool items per run
OUTPUT_DIR     = "data"
NEWS_FILE      = f"{OUTPUT_DIR}/news.json"
TOOLS_FILE     = f"{OUTPUT_DIR}/tools_new.json"
TODAY          = datetime.date.today().isoformat()

AI_KEYWORDS = [
    "AI", "artificial intelligence", "LLM", "GPT", "Claude", "Gemini",
    "machine learning", "automation", "agent", "chatbot", "copilot",
    "generative", "openai", "anthropic", "mistral", "llama", "deepseek"
]

CATEGORIES = ["Writing", "Coding", "Automation", "Design", "Video",
              "Marketing", "Productivity", "Search", "Research", "Other"]


# ── HELPERS ───────────────────────────────────────────────────────────────────
def fetch_json(url: str, timeout: int = 10) -> dict | list | None:
    """HTTP GET → parsed JSON, returns None on error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ToolsDirectoryBot/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  [WARN] fetch_json({url}) failed: {e}")
        return None


def is_ai_related(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in AI_KEYWORDS)


def clean_text(text: str, max_len: int = 300) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ").strip()
    return text[:max_len] + ("…" if len(text) > max_len else "")


# ── DATA SOURCES ──────────────────────────────────────────────────────────────
def fetch_hackernews() -> list[dict]:
    """Fetch AI-related posts from HackerNews (last 3 days)."""
    print("📡 Fetching HackerNews…")
    items = []
    cutoff = int(datetime.datetime.now().timestamp()) - 86400 * 3
    url = (
        "https://hn.algolia.com/api/v1/search"
        f"?query=AI+tools&tags=story&numericFilters=created_at_i>{cutoff}"
    )
    data = fetch_json(url)
    if not data:
        return items
    for hit in data.get("hits", [])[:20]:
        title = hit.get("title", "")
        if not is_ai_related(title):
            continue
        items.append({
            "id":       hit.get("objectID", ""),
            "title":    title,
            "url":      hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "source":   "HackerNews",
            "points":   hit.get("points", 0),
            "date":     TODAY,
            "summary":  clean_text(title),
            "category": "Other",
            "tags":     ["AI", "HackerNews"],
        })
    print(f"  → {len(items)} items from HackerNews")
    return items


def fetch_devto() -> list[dict]:
    """Fetch AI articles from Dev.to public API (no key needed)."""
    print("📡 Fetching Dev.to…")
    items = []
    url = "https://dev.to/api/articles?tag=ai&per_page=20&top=3"
    data = fetch_json(url)
    if not isinstance(data, list):
        return items
    for art in data:
        title = art.get("title", "")
        if not is_ai_related(title):
            continue
        items.append({
            "id":       str(art.get("id", "")),
            "title":    title,
            "url":      art.get("url", ""),
            "source":   "Dev.to",
            "points":   art.get("public_reactions_count", 0),
            "date":     TODAY,
            "summary":  clean_text(art.get("description", title)),
            "category": "Other",
            "tags":     art.get("tag_list", ["AI"]),
        })
    print(f"  → {len(items)} items from Dev.to")
    return items


def fetch_producthunt_rss() -> list[dict]:
    """Fetch Product Hunt RSS via rss2json free tier (10k req/month)."""
    print("📡 Fetching Product Hunt RSS…")
    items = []
    rss_url = "https://www.producthunt.com/feed"
    api_url = f"https://api.rss2json.com/v1/api.json?rss_url={urllib.parse.quote(rss_url)}&count=20"
    data = fetch_json(api_url)
    if not data or data.get("status") != "ok":
        return items
    for entry in data.get("items", []):
        title = entry.get("title", "")
        if not is_ai_related(title + entry.get("description", "")):
            continue
        items.append({
            "id":       entry.get("guid", entry.get("link", "")),
            "title":    title,
            "url":      entry.get("link", ""),
            "source":   "Product Hunt",
            "points":   0,
            "date":     TODAY,
            "summary":  clean_text(entry.get("description", "")),
            "category": "Other",
            "tags":     ["AI", "Product Hunt"],
        })
    print(f"  → {len(items)} items from Product Hunt")
    return items


# ── GEMINI AI ENRICHMENT ──────────────────────────────────────────────────────
def enrich_with_gemini(items: list[dict]) -> list[dict]:
    """
    Use Google Gemini 1.5 Flash to write better summaries + pick categories.
    Only runs when GEMINI_API_KEY is set.

    Free tier limits (as of 2025):
      - gemini-1.5-flash: 1,500 requests/day, 1,000,000 tokens/min — more than enough.
    Get a free key at: https://aistudio.google.com/apikey
    """
    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY not set — skipping AI enrichment")
        return items

    print(f"✨ Enriching {len(items)} items with Gemini 1.5 Flash…")
    cats_str = ", ".join(CATEGORIES)

    # Gemini REST endpoint
    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    for item in items:
        prompt = (
            f"Title: {item['title']}\n"
            f"Summary: {item['summary']}\n\n"
            f"1. Write a 1-sentence description (max 120 chars) for an AI tools directory.\n"
            f"2. Pick the best category from: {cats_str}\n\n"
            f"Reply ONLY as valid JSON with no markdown fences:\n"
            f"{{\"summary\": \"...\", \"category\": \"...\"}}"
        )

        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature":    0.2,
                "maxOutputTokens": 150,
            }
        }).encode()

        try:
            req = urllib.request.Request(
                api_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode())

            # Extract text from Gemini response structure
            text = (
                result["candidates"][0]["content"]["parts"][0]["text"]
                .strip()
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )
            enriched = json.loads(text)
            item["summary"]  = enriched.get("summary",  item["summary"])
            item["category"] = enriched.get("category", item["category"])
            print(f"  ✔ [{item['category']}] {item['title'][:60]}")

        except Exception as e:
            print(f"  [WARN] Gemini enrichment failed for '{item['title'][:50]}': {e}")

    print(f"  → Done enriching {len(items)} items")
    return items


# ── DEDUP + MERGE ─────────────────────────────────────────────────────────────
def load_existing(filepath: str) -> list[dict]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def merge_and_dedup(existing: list[dict], new_items: list[dict]) -> list[dict]:
    seen_ids  = {item["id"]  for item in existing}
    seen_urls = {item["url"] for item in existing}
    merged = list(existing)
    for item in new_items:
        if item["id"] not in seen_ids and item["url"] not in seen_urls:
            merged.append(item)
            seen_ids.add(item["id"])
            seen_urls.add(item["url"])
    merged.sort(key=lambda x: x.get("date", ""), reverse=True)
    return merged[:MAX_ITEMS * 5]   # rolling window: keep last 50 items


# ── WRITE JSON ────────────────────────────────────────────────────────────────
def save_json(filepath: str, data) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Saved → {filepath}  ({len(data)} items)")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*55}")
    print(f"  ToolsDirectory Agent  —  {TODAY}")
    print(f"  AI engine: Gemini 1.5 Flash (FREE tier)")
    print(f"{'='*55}\n")

    # 1. Collect from all free sources
    raw = []
    raw += fetch_hackernews()
    raw += fetch_devto()
    raw += fetch_producthunt_rss()
    print(f"\n📦 Total raw items collected: {len(raw)}")

    if not raw:
        print("⚠️  No items collected — exiting without writing files.")
        return

    # 2. Deduplicate within this batch
    seen, unique = set(), []
    for item in raw:
        key = item["url"] or item["title"]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 3. Gemini AI enrichment (optional, free)
    unique = enrich_with_gemini(unique)

    # 4. Latest news feed (top N items)
    latest = unique[:MAX_ITEMS]

    # 5. Merge with existing rolling history
    existing_news  = load_existing(NEWS_FILE)
    existing_tools = load_existing(TOOLS_FILE)
    merged_news    = merge_and_dedup(existing_news,  latest)
    merged_tools   = merge_and_dedup(existing_tools, unique)

    # 6. Save JSON files
    print()
    save_json(NEWS_FILE,  merged_news)
    save_json(TOOLS_FILE, merged_tools)

    # 7. Metadata file (site reads this for "last updated" badge)
    meta = {
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "total_news":   len(merged_news),
        "total_tools":  len(merged_tools),
        "ai_engine":    f"Gemini {GEMINI_MODEL}" if GEMINI_API_KEY else "none",
        "sources":      ["HackerNews", "Dev.to", "Product Hunt"],
    }
    save_json(f"{OUTPUT_DIR}/meta.json", meta)

    print(f"\n🎉 Done! Files written to /{OUTPUT_DIR}/\n")


if __name__ == "__main__":
    main()
