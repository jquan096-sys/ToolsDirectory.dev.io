# 🤖 ToolsDirectory Auto-Update Agent (Gemini Edition)

Automatically fetches the latest AI tool news, enriches it with **Google Gemini 1.5 Flash** (free), and updates your GitHub Pages site every day — no server needed.

---

## 📁 Files to add to your repo

```
your-repo/
├── agent_update.py                   ← the agent script (uses Gemini API)
├── news-loader.js                    ← drop into your site JS
├── news-styles.css                   ← drop into your site CSS
├── data/
│   ├── news.json                     ← auto-updated daily
│   ├── tools_new.json                ← auto-updated daily
│   └── meta.json                     ← last-run metadata
└── .github/
    └── workflows/
        └── auto_update.yml           ← GitHub Actions schedule
```

---

## ⚙️ Setup (5 minutes)

### Step 1 — Get your FREE Gemini API Key

1. Go to → **https://aistudio.google.com/apikey**
2. Sign in with Google
3. Click **Create API Key**
4. Copy the key

> **Free tier:** 1,500 requests/day · 1,000,000 tokens/min — plenty for daily updates.

### Step 2 — Add the key to GitHub Secrets

1. Open your repo on GitHub
2. **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Name: `GEMINI_API_KEY`
5. Value: paste your key → **Add secret**

### Step 3 — Enable Actions write permission

1. **Settings → Actions → General**
2. Scroll to **Workflow permissions**
3. Select ✅ **Read and write permissions** → Save

### Step 4 — Copy all files into your repo

Copy the files keeping the folder structure (`.github/workflows/` is important).

### Step 5 — Add the news feed to your HTML

```html
<!-- In <head> -->
<link rel="stylesheet" href="/news-styles.css">

<!-- In page body, wherever you want the feed -->
<section>
  <h2>🔥 Latest AI Tool News</h2>
  <div id="ai-news"></div>
</section>

<!-- Before </body> -->
<script src="/news-loader.js"></script>
```

### Step 6 — Test it manually

Go to **Actions tab → 🤖 Auto-Update AI Tools News → Run workflow**

You should see `data/news.json` committed with fresh AI-summarized items.

---

## 🕐 Schedule

Default: **every day at 08:00 UTC**. Edit in `auto_update.yml`:

```yaml
- cron: "0 8 * * *"     # daily at 8am UTC
- cron: "0 8 * * 1"     # every Monday only
- cron: "0 */6 * * *"   # every 6 hours
```

---

## 📡 What it fetches (all free, no key needed)

| Source | Data | Limit |
|--------|------|-------|
| HackerNews Algolia | AI startup & tool posts | Unlimited |
| Dev.to | AI developer articles | Unlimited |
| Product Hunt RSS via rss2json | New AI tool launches | 10k req/month |

---

## 🧠 How Gemini enriches each item

For every news item, Gemini writes:
- A clean 1-sentence description (max 120 chars)
- The best category from: Writing, Coding, Automation, Design, Video, Marketing, Productivity, Search, Research, Other

---

## 💡 Flow diagram

```
GitHub Actions (cron: daily)
        ↓
agent_update.py runs
        ↓
Fetches HackerNews + Dev.to + Product Hunt
        ↓
Gemini 1.5 Flash summarizes + categorizes (FREE)
        ↓
Writes data/news.json + data/tools_new.json + data/meta.json
        ↓
Git commit + push → GitHub Pages serves fresh JSON
        ↓
news-loader.js on your site fetches and renders cards
```
