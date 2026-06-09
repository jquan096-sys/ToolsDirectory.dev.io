name: 🤖 Auto-Update AI Tools News

on:
  schedule:
    # Run every 6 hours (4x per day)
    - cron: "0 */6 * * *"
  
  # Allow manual trigger from GitHub UI
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run agent_update.py
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          AGENT_NAME: "ToolsDirectoryBot/3.0-Dual"
        run: python agent_update.py

      - name: Commit & push changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "🤖 Auto-update: Fresh AI news + verified tools (via agent)"
          file_pattern: "data/*.json index.html"
          commit_user_name: "github-actions[bot]"
          commit_user_email: "github-actions[bot]@users.noreply.github.com"
