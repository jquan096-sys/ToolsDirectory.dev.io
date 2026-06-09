// ── NEWS LOADER (LIVE UPDATES) ─────────────────────────────────────────────
// Automatically fetches and displays verified AI news cards every time the page loads
// Shows: Title | Link | Date | Category | Summary | ✅ Verified Badge

async function loadNews() {
  const container = document.getElementById("ai-news");
  const updatedEl = document.getElementById("last-updated");

  if (!container) return;

  try {
    // Fetch metadata first
    const metaRes = await fetch("data/meta.json?cb=" + Date.now());
    if (metaRes.ok) {
      const meta = await metaRes.json();
      const d = new Date(meta.last_updated);
      const verifyBadge = meta.verification_status || "🔄 Syncing...";
      
      updatedEl.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:1rem; padding:0.875rem; background:#ecfdf5; border-radius:10px; border:1px solid #a7f3d0; font-size:0.8rem;">
          <span style="color:#065f46;"><strong>📡 Last Updated:</strong> ${d.toLocaleString()} UTC</span>
          <span style="color:#059669; font-weight:700;">${verifyBadge}</span>
        </div>
      `;
      
      // Update news count in stats
      if (document.getElementById("stat-news")) {
        document.getElementById("stat-news").textContent = meta.total_news || "12";
      }
    }

    // Fetch news items
    const res = await fetch("data/news.json?cb=" + Date.now());
    if (!res.ok) throw new Error("news.json not found (HTTP " + res.status + ")");

    const items = await res.json();
    if (!items || items.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:2rem; color:#6b7280; font-style:italic;">
          📭 No news available yet. Check back soon!
        </div>
      `;
      return;
    }

    // Render news cards (max 12)
    container.innerHTML = items.slice(0, 12).map((item) => {
      const sourceClass = (item.source || "").toLowerCase().replace(/\s+/g, "");
      const categoryColor = getCategoryColor(item.category);
      const sourceColor = getSourceColor(sourceClass);
      const verifiedBadge = item.verified 
        ? `<span style="display:inline-block; margin-left:0.5rem; padding:3px 8px; background:#d1fae5; color:#059669; font-size:0.7rem; font-weight:700; border-radius:4px; white-space:nowrap;">✅ VERIFIED</span>`
        : "";

      return `
        <a 
          href="${escapeHtml(item.url)}" 
          target="_blank" 
          rel="noopener noreferrer"
          style="
            display:flex; 
            flex-direction:column; 
            gap:8px; 
            padding:16px; 
            border:1px solid #e5e7eb; 
            border-radius:12px; 
            background:#fff; 
            text-decoration:none; 
            color:inherit; 
            transition:all 0.2s ease;
            cursor:pointer;
          "
          onmouseenter="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'; this.style.transform='translateY(-2px)'; this.style.borderColor='${sourceColor}';"
          onmouseleave="this.style.boxShadow='none'; this.style.transform='translateY(0)'; this.style.borderColor='#e5e7eb';"
        >
          <!-- Source Badge + Verified Badge -->
          <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
            <span style="display:inline-block; padding:3px 10px; border-radius:20px; font-size:0.7rem; font-weight:700; color:#fff; background:${sourceColor}; text-transform:uppercase;">
              ${escapeHtml(item.source || "Other")}
            </span>
            ${verifiedBadge}
          </div>
          
          <!-- Category Badge -->
          <span style="display:inline-block; padding:4px 10px; background:${categoryColor}; color:#fff; font-size:0.75rem; font-weight:700; border-radius:6px; width:fit-content; text-transform:uppercase; letter-spacing:0.05em;">
            📂 ${escapeHtml(item.category || "Other")}
          </span>
          
          <!-- Title -->
          <strong style="font-size:14px; line-height:1.4; color:#1a1a2e;">
            ${escapeHtml(item.title || "Untitled")}
          </strong>
          
          <!-- Summary -->
          <p style="font-size:12px; color:#5f6368; margin:0; line-height:1.5;">
            ${escapeHtml(item.summary || "")}
          </p>
          
          <!-- Footer: Date + Read Link -->
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:auto; font-size:0.8rem; color:#80868b; border-top:1px solid #f3f4f6; padding-top:8px;">
            <span style="font-weight:500;">📅 ${escapeHtml(item.date || "")}</span>
            <span style="color:#2563eb; font-weight:600; text-decoration:none;">Read Article →</span>
          </div>
        </a>
      `;
    }).join("");

  } catch (err) {
    container.innerHTML = `
      <div style="text-align:center; padding:2rem; background:#fee2e2; border-radius:10px; border:1px solid #fecaca; color:#991b1b;">
        <p style="margin:0 0 0.5rem 0;"><strong>⚠️ Could not load news feed</strong></p>
        <p style="margin:0; font-size:0.85rem; color:#7f1d1d;">${err.message}</p>
      </div>
    `;
    console.error("loadNews error:", err);
  }
}

// ── HELPER FUNCTIONS ────────────────────────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

function getSourceColor(source) {
  const colors = {
    "hackernews": "#ff6600",
    "devto": "#3b49df",
    "dev.to": "#3b49df",
    "producthunt": "#da552f",
    "product hunt": "#da552f"
  };
  return colors[source] || "#6b7280";
}

function getCategoryColor(category) {
  const colors = {
    "Writing": "#7c3aed",      // Purple
    "Coding": "#2563eb",        // Blue
    "Automation": "#059669",    // Green
    "Design": "#dc2626",        // Red
    "Video": "#f97316",         // Orange
    "Marketing": "#db2777",     // Pink
    "Productivity": "#0891b2",  // Cyan
    "Search": "#7c3aed",        // Purple
    "Research": "#2563eb",      // Blue
    "Other": "#6b7280"          // Gray
  };
  return colors[category] || colors["Other"];
}

// ── INITIALIZE ──────────────────────────────────────────────────────────────
// Load news when page is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", loadNews);
} else {
  loadNews();
}

// Optional: Refresh news every 5 minutes while page is open
setInterval(loadNews, 5 * 60 * 1000);
