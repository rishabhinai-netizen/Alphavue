/**
 * AlphaVue v2 — Breeze API Proxy
 * Vercel Serverless Function
 * 
 * POST /api/breeze-quotes
 * Body: { apiKey, sessionToken, symbols: ["RELIND","TATACO",...] }
 * Returns: { RELIND: { ltp: 2847.5, change: 1.2, changeAmt: 34.1 }, ... }
 * 
 * Why a proxy? Breeze REST API requires HMAC-SHA256 signing server-side.
 * Doing this in browser would expose your secret key.
 */

const https = require('https');
const crypto = require('crypto');

// Breeze stock code mapping: NSE symbol → Breeze stockCode
// Breeze uses its own internal codes (different from NSE symbols for some stocks)
const SYMBOL_MAP = {
  'RELIANCE': 'RELIND', 'TCS': 'TATACO', 'HDFCBANK': 'HDFBAN', 'INFY': 'INFYSY',
  'ICICIBANK': 'ICICIB', 'KOTAKBANK': 'KOTAKB', 'SBIN': 'STABAN', 'BHARTIARTL': 'BHARTE',
  'WIPRO': 'WIPROC', 'AXISBANK': 'AXIBAN', 'LT': 'LARTOU', 'ITC': 'ITCLIM',
  'HCLTECH': 'HCLITE', 'BAJFINANCE': 'BAJFIN', 'TITAN': 'TITIND',
  'MCX': 'MULTICM', 'NATIONALUM': 'NATAUM', 'ATHERENERG': 'ATHENE',
  'WELCORP': 'WELSPU', 'ADANIPOWER': 'ADANIP', 'GALLANTT': 'GALLAT',
  // For symbols not in map, try the raw symbol (works for most Nifty 500 stocks)
};

function getBreezeCode(nseSymbol) {
  return SYMBOL_MAP[nseSymbol] || nseSymbol;
}

function makeChecksum(apiSecret, timestamp) {
  // Breeze checksum: SHA256(timestamp + apiSecret)
  return crypto
    .createHash('sha256')
    .update(timestamp + apiSecret)
    .digest('hex');
}

async function fetchQuote(symbol, apiKey, sessionToken, apiSecret) {
  const timestamp = new Date().toISOString();
  const checksum = makeChecksum(apiSecret, timestamp);
  const breezeCode = getBreezeCode(symbol);

  const url = `https://api.icicidirect.com/breezeapi/api/v1/quotes?` +
    `stockCode=${breezeCode}&exchangeCode=NSE&productType=cash&expiryDate=&right=&strikePrice=`;

  return new Promise((resolve) => {
    const options = {
      method: 'GET',
      headers: {
        'X-Checksum': `token ${checksum}`,
        'X-Timestamp': timestamp,
        'X-AppKey': apiKey,
        'X-SessionToken': sessionToken,
        'Content-Type': 'application/json',
      }
    };

    const req = https.get(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(data);
          if (json.Status === 200 && json.Success && json.Success.length > 0) {
            const q = json.Success[0];
            resolve({
              ltp: parseFloat(q.ltp || q.last_rate || 0),
              open: parseFloat(q.open || 0),
              high: parseFloat(q.high || 0),
              low: parseFloat(q.low || 0),
              prev_close: parseFloat(q.previous_close || q.prev_close || 0),
              volume: parseInt(q.total_quantity_traded || 0),
              change_pct: parseFloat(q.change_percent || q.percentage_change || 0),
              change_amt: parseFloat(q.change || 0),
              ok: true
            });
          } else {
            resolve({ ltp: 0, ok: false, error: json.Error || 'No data' });
          }
        } catch (e) {
          resolve({ ltp: 0, ok: false, error: 'Parse error' });
        }
      });
    });
    req.on('error', (e) => resolve({ ltp: 0, ok: false, error: e.message }));
    req.setTimeout(5000, () => { req.destroy(); resolve({ ltp: 0, ok: false, error: 'Timeout' }); });
  });
}

module.exports = async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'POST only' });

  const { apiKey, sessionToken, apiSecret, symbols } = req.body || {};

  if (!apiKey || !sessionToken || !symbols || !Array.isArray(symbols)) {
    return res.status(400).json({ error: 'Missing apiKey, sessionToken, or symbols[]' });
  }

  if (symbols.length > 50) {
    return res.status(400).json({ error: 'Max 50 symbols per request' });
  }

  // Fetch all quotes in parallel
  const results = await Promise.all(
    symbols.map(sym => fetchQuote(sym, apiKey, sessionToken, apiSecret || '').then(q => [sym, q]))
  );

  const quotes = Object.fromEntries(results);
  res.status(200).json({ quotes, timestamp: new Date().toISOString() });
};
