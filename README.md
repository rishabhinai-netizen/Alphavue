# AlphaVue v2

> Nifty 500 real-time intelligence. Because a spreadsheet isn't a dashboard.

A live market intelligence dashboard for NSE traders covering the full Nifty 500 universe — real-time prices via ICICI Breeze API, auto-refreshing, dark UI, deployable on Vercel in under 15 minutes.

---

## What It Shows

- **Live Prices** — Real-time Nifty 500 quotes via Breeze API, auto-refreshed
- **Momentum Signals** — Price vs 20/50/200 DMA positioning at a glance
- **Volume Intelligence** — Current volume vs rolling average — who's moving
- **Sector Heatmap** — Colour-coded performance by sector in real time
- **Movers & Shakers** — Top gainers, losers, and volume outliers
- **Watchlist Layer** — Custom stock watchlists with alert thresholds

## Architecture

```
AlphaVue/
├── index.html          # Single-page application entry
├── scripts/            # JS modules — data fetch, rendering, refresh logic
├── api/                # Breeze API wrapper and price normalisation
├── data/               # Static reference data (stock universe, sector mapping)
└── vercel.json         # One-click Vercel deployment config
```

## Deploy in 15 Minutes

### Step 1 — Fork this repo on GitHub

### Step 2 — Get Breeze API credentials
1. Log into ICICI Direct
2. Go to API portal → Generate API key and secret
3. Get a fresh session token daily (or automate via the Breeze login flow)

### Step 3 — Deploy to Vercel
1. Go to [vercel.com](https://vercel.com) → New Project → Import this repo
2. Add environment variables:
   ```
   BREEZE_API_KEY=your_key
   BREEZE_API_SECRET=your_secret
   BREEZE_SESSION_TOKEN=your_daily_token
   ```
3. Click Deploy

### Step 4 — Open your dashboard
Live in under 2 minutes from deploy.

## Session Token Note

Breeze session tokens expire daily. For continuous operation, refresh the token each morning via the Breeze API login flow and update the environment variable in Vercel.

## Tech Stack

- Vanilla JavaScript — no framework overhead, fast load
- ICICI Breeze API — official NSE data feed
- Vercel — edge deployment, free tier sufficient
- CSS Grid — responsive layout for any screen size

---

*Part of a broader suite of NSE trading tools. See also: [RS-screener](https://github.com/rishabhinai-netizen/RS-screener), [dc-backtester](https://github.com/rishabhinai-netizen/dc-backtester)*
