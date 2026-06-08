# 🤖 ToolsDirectory Auto-Update Agent

Automatically fetches the latest AI tool news and updates your GitHub Pages site every day — **free, no server needed**.

---

## 📁 Files to add to your repo

```
your-repo/
├── agent_update.py                   ← the agent script
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

### Step 1 — Copy files into your repo

Copy all files above into your `jquan096-sys/ToolsDirectory.dev.io` repository.

### Step 2 — Enable GitHub Actions write permission

1. Go to your repo on GitHub
2. **Settings → Actions → General**
3. Scroll to **Workflow permissions**
4. Select ✅ **Read and write permissions**
5. Click **Save**

### Step 3 — (Optional) Add Claude API key for better summaries

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your key from https://console.anthropic.com

> Without this key the agent still works — it just skips AI-generated summaries.

### Step 4 — Add the news feed to your HTML

Wherever you want the news to appear, add:

```html
<!-- In your <head> -->
<link rel="stylesheet" href="/news-styles.css">

<!-- In your page body -->
<section>
  <h2>🔥 Latest AI Tool News</h2>
  <div id="ai-news"></div>
</section>

<!-- Before </body> -->
<script src="/news-loader.js"></script>
```

### Step 5 — Test it manually

Go to **Actions tab → 🤖 Auto-Update AI Tools News → Run workflow**

You should see `data/news.json` get committed with fresh items.

---

## 🕐 Schedule

The agent runs **every day at 08:00 UTC** by default.

To change the schedule, edit `.github/workflows/auto_update.yml`:

```yaml
- cron: "0 8 * * *"    # daily at 8am UTC
- cron: "0 8 * * 1"    # every Monday
- cron: "0 */6 * * *"  # every 6 hours
```

---

## 📡 Free APIs Used (no key required)

| Source | Data | Limit |
|--------|------|-------|
| HackerNews Algolia | AI startup/tool posts | Unlimited |
| Dev.to | AI developer articles | Unlimited |
| Product Hunt RSS via rss2json | New AI tool launches | 10k req/month free |

---

## 💡 How it works

```
GitHub Actions (cron: daily)
        ↓
agent_update.py runs
        ↓
Fetches HackerNews + Dev.to + Product Hunt
        ↓
(Optional) Claude Haiku summarizes + categorizes
        ↓
Writes data/news.json + data/tools_new.json
        ↓
Git commit + push → GitHub Pages serves fresh JSON
        ↓
news-loader.js on your site fetches and renders it
```
