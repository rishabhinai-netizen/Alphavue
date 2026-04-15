# AlphaVue v2 — Nifty 500 Intelligence
**Live · Real-time Breeze prices · Auto-refreshing · Dark UI**

---

## Quick deploy (15 minutes, no coding needed)

### Step 1 — Put the code on GitHub
1. Go to [github.com](https://github.com) and sign in (or create free account)
2. Click **+** → **New repository** → name it `alphavue-v2` → **Create repository**
3. Click **uploading an existing file**
4. Drag all files from this folder into the upload box
5. Click **Commit changes** → Done

### Step 2 — Deploy to Vercel (free)
1. Go to [vercel.com](https://vercel.com) and sign in with your GitHub account
2. Click **Add New Project**
3. Select your `alphavue-v2` repository
4. Click **Deploy** — that's it

Your live URL will be: `https://alphavue-v2.vercel.app`

### Step 3 — Connect your Breeze API
1. Open your AlphaVue URL
2. Click **Connect Breeze** in the top-right
3. Enter your ICICI Direct API Key, API Secret, and today's Session Token
4. Click **Connect** — live prices start flowing every 30 seconds

**Getting session token daily:**
- Log into ICICI Direct → API console → generate session token
- Paste into AlphaVue's Breeze settings
- Token expires at midnight; paste fresh one each morning

---

## Weekly auto-refresh (set up once, then never touch)

The app scores all 500 Nifty stocks weekly via a GitHub Action.

1. In your GitHub repo, go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions", select **Read and write permissions** → Save
3. That's it — every Sunday at 6 PM IST, scores auto-update and the site auto-deploys

To run a manual refresh: GitHub repo → **Actions** → **Weekly Score Refresh** → **Run workflow**

---

## Daily Breeze token automation (optional, via n8n)

Since Breeze session tokens expire daily, you can automate this:
1. In n8n, create a workflow that runs at 9:00 AM IST
2. Use the ICICI Direct login API to generate a fresh token
3. POST it to `/api/update-token` (endpoint in `api/update-token.js`)
4. AlphaVue picks it up automatically

This is the n8n automation you were already planning in April 2026.

---

## Scoring model summary

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| Momentum (RS rank) | 35% | Percentile rank vs 500 peers, multi-TF |
| Trend (Stage 2) | 25% | Price > MA20 > MA50 > MA200 |
| Volume confirmation | 15% | 5d/20d vol ratio |
| Consistency | 15% | % days up in 20d |
| Risk-adjusted | 10% | Calmar ratio |

**Honest backtest (1 year, Apr 2025–Apr 2026):**
- Daily signals: ~49% win rate (near-random)
- Swing (Vol≥1.3×, 10d hold): 51% win rate, +0.18% avg
- 15-day proof: +16.38% (regime-specific bull rally)

---

## Signal types

| Signal | Criteria | Hold | Win rate |
|--------|----------|------|---------|
| Intraday | Vol≥2× + within 5% of 52H + S/A | Same day | Market-dependent |
| Swing | Vol≥1.3× + RS≥80 + Stage2 + 52H | 5–10 days | ~51% |
| Positional | S-grade + full Stage2 | Weekly hold | Regime-dependent |

**Golden rule: Check market regime first.** If Nifty 50 is below its 50-day MA, reduce position size by 50% or sit out entirely.

---

## Files
```
alphavue-v2/
├── index.html                    ← Main app (all-in-one)
├── api/
│   └── breeze-quotes.js          ← Vercel serverless: Breeze proxy
├── data/
│   └── scores.json               ← Pre-computed scores (auto-updated weekly)
├── scripts/
│   └── build_data.py             ← Score computation (run by GitHub Action)
├── .github/workflows/
│   └── refresh-scores.yml        ← Weekly automation
├── vercel.json                   ← Deploy config
└── README.md                     ← This file
```
