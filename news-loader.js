/**
 * news-loader.js
 * ==============
 * Drop this in your site and add <div id="ai-news"></div> wherever
 * you want the live news feed to appear.
 *
 * It reads  /data/news.json  (committed by agent_update.py via GitHub Actions)
 * and renders the latest AI tool news cards automatically.
 */

(async function loadAINews() {
  const container = document.getElementById("ai-news");
  if (!container) return;

  // ── Show skeleton loader ──────────────────────────────────────────────────
  container.innerHTML = `
    <div class="news-loading">
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
      <div class="skeleton-card"></div>
    </div>`;

  try {
    // Cache-bust so GitHub Pages serves fresh JSON each load
    const res  = await fetch(`/data/news.json?v=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const news = await res.json();

    // ── Read meta for "last updated" badge ───────────────────────────────
    let lastUpdated = "";
    try {
      const metaRes = await fetch(`/data/meta.json?v=${Date.now()}`);
      const meta    = await metaRes.json();
      const d = new Date(meta.last_updated);
      lastUpdated = d.toLocaleDateString("en-US", { month:"short", day:"numeric", year:"numeric" });
    } catch (_) {}

    // ── Render ─────────────────────────────────────────────────────────────
    const header = lastUpdated
      ? `<p class="news-meta">🔄 Last updated: <strong>${lastUpdated}</strong></p>`
      : "";

    const cards = news.slice(0, 10).map(item => `
      <a class="news-card" href="${escHtml(item.url)}" target="_blank" rel="noopener">
        <span class="news-badge ${badgeClass(item.source)}">${escHtml(item.source)}</span>
        <span class="news-category">${escHtml(item.category)}</span>
        <h3 class="news-title">${escHtml(item.title)}</h3>
        <p  class="news-summary">${escHtml(item.summary)}</p>
        <span class="news-date">${escHtml(item.date)}</span>
      </a>`).join("");

    container.innerHTML = header + `<div class="news-grid">${cards}</div>`;

  } catch (err) {
    container.innerHTML = `<p class="news-error">⚠️ Could not load latest news. <a href="#">Retry</a></p>`;
    console.warn("news-loader:", err);
  }

  // ── Helpers ──────────────────────────────────────────────────────────────
  function escHtml(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function badgeClass(source) {
    const map = {
      "HackerNews":    "badge-hn",
      "Dev.to":        "badge-devto",
      "Product Hunt":  "badge-ph",
    };
    return map[source] || "badge-default";
  }
})();
