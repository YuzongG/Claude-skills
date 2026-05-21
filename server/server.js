const TradingView = require('@mathieuc/tradingview');
const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

const PORT = 8080;

// Ticker → TradingView symbol (exchange:ticker format)
const SYMBOLS = {
  KLAC: 'NASDAQ:KLAC',
  ONTO: 'NYSE:ONTO',
  AMAT: 'NASDAQ:AMAT',
  LRCX: 'NASDAQ:LRCX',
  ASML: 'NASDAQ:ASML',
  CDNS: 'NASDAQ:CDNS',
  SNPS: 'NASDAQ:SNPS',
  RMBS: 'NASDAQ:RMBS',
  INTC: 'NASDAQ:INTC',
  NVDA: 'NASDAQ:NVDA',
  AVGO: 'NASDAQ:AVGO',
  MCHP: 'NASDAQ:MCHP',
  QUIK: 'NASDAQ:QUIK',
  SIMO: 'NASDAQ:SIMO',
  MU:   'NASDAQ:MU',
  AAOI: 'NASDAQ:AAOI',
  NOK:  'NYSE:NOK',
  COHR: 'NYSE:COHR',
  MRVL: 'NASDAQ:MRVL',
  ANET: 'NYSE:ANET',
  SMCI: 'NASDAQ:SMCI',
  P:    'NYSE:P',    // Everpure (formerly Pure Storage / PSTG)
  VRT:  'NYSE:VRT',
  AMZN: 'NASDAQ:AMZN',
  NBIS: 'NASDAQ:NBIS',
  HUT:  'NASDAQ:HUT',
  IREN: 'NASDAQ:IREN',
  MSFT: 'NASDAQ:MSFT',
  AMD:  'NASDAQ:AMD',
  ARM:  'NASDAQ:ARM',
  // ── Robotics chart additions ───────────────────────────────────────────
  RRX:  'NYSE:RRX',     // Regal Rexnord — precision gearboxes
  TKR:  'NYSE:TKR',     // Timken — bearings
  AME:  'NYSE:AME',     // Ametek — precision motion
  QCOM: 'NASDAQ:QCOM',  // Qualcomm — Dragonwing robotics chips
  TXN:  'NASDAQ:TXN',   // Texas Instruments — motor control ICs
  ADI:  'NASDAQ:ADI',   // Analog Devices — IMU/MEMS
  CGNX: 'NASDAQ:CGNX',  // Cognex — machine vision
  OUST: 'NYSE:OUST',    // Ouster — LiDAR
  AEVA: 'NASDAQ:AEVA',  // Aeva — FMCW LiDAR
  TDY:  'NYSE:TDY',     // Teledyne — FLIR thermal/vision
  ROK:  'NYSE:ROK',     // Rockwell Automation
  EMR:  'NYSE:EMR',     // Emerson Electric
  ABB:  'NYSE:ABB',     // ABB Ltd (ADR)
  TER:  'NASDAQ:TER',   // Teradyne — Universal Robots + MiR
  SYM:  'NASDAQ:SYM',   // Symbotic — warehouse robotics
  ISRG: 'NASDAQ:ISRG',  // Intuitive Surgical — da Vinci
  MDT:  'NYSE:MDT',     // Medtronic — Hugo RAS
  SYK:  'NYSE:SYK',     // Stryker — Mako orthopedic
  TSLA: 'NASDAQ:TSLA',  // Tesla — Optimus humanoid
  AVAV: 'NASDAQ:AVAV',  // AeroVironment — drones
  WMT:  'NYSE:WMT',     // Walmart — Symbotic deployment
};

// ── HTTP + WebSocket server ───────────────────────────────────────────────────
const HTML_PATH = path.join(__dirname, '..', 'charts', 'ai-supply-chain.html');

const httpServer = http.createServer((req, res) => {
  // Serve the chart HTML at root
  if (req.url === '/' || req.url === '/index.html') {
    fs.readFile(HTML_PATH, (err, data) => {
      if (err) {
        res.writeHead(404); res.end('HTML not found: ' + HTML_PATH); return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(data);
    });
    return;
  }
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('AI Supply Chain server running — open http://localhost:8080\n');
});

const wss = new WebSocket.Server({ server: httpServer });

// Latest quote cache (so new browser tabs get instant data)
const quoteCache = {};

function broadcast(msg) {
  const str = JSON.stringify(msg);
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) client.send(str);
  });
}

wss.on('connection', (ws) => {
  console.log(`[WS] Client connected  (total: ${wss.clients.size})`);

  // Send all cached quotes immediately on connect
  Object.values(quoteCache).forEach(q => {
    ws.send(JSON.stringify({ type: 'quote', ...q }));
  });

  ws.on('close', () => {
    console.log(`[WS] Client disconnected (total: ${wss.clients.size})`);
  });
});

// ── TradingView connection ────────────────────────────────────────────────────
let tvClient = null;
let markets  = [];

function startTradingView() {
  console.log('[TV] Connecting to TradingView…');

  tvClient = new TradingView.Client();
  const session = new tvClient.Session.Quote({ fields: 'all' });

  Object.entries(SYMBOLS).forEach(([ticker, tvSymbol]) => {
    const market = new session.Market(tvSymbol);
    markets.push(market);

    market.onData((data) => {
      const price     = data.lp               ?? null;
      const prevClose = data.prev_close_price ?? null;
      const volume    = data.volume           ?? null;
      const high      = data.high_price       ?? null;
      const low       = data.low_price        ?? null;

      // Compute standard "vs yesterday's close" change (same as most brokers/apps).
      // TradingView's rchp is intraday-only (vs today's open), which diverges from
      // the conventional definition users expect.
      const change    = (price != null && prevClose != null) ? price - prevClose : null;
      const changePct = (price != null && prevClose != null && prevClose !== 0)
        ? (price - prevClose) / prevClose * 100
        : null;

      if (price == null) return;

      const quote = { ticker, price, change, changePct, volume, high, low, prevClose };
      quoteCache[ticker] = quote;
      broadcast({ type: 'quote', ...quote });

      process.stdout.write(
        `\r[${ticker.padEnd(5)}] $${price.toFixed(2).padStart(10)}  ${(changePct ?? 0) >= 0 ? '+' : ''}${(changePct ?? 0).toFixed(2)}%   `
      );
    });

    market.onError((...args) => {
      console.error(`\n[TV] ${ticker} error:`, ...args);
    });
  });

  tvClient.onError = (err) => {
    console.error('\n[TV] Client error — reconnecting in 5s:', err.message ?? err);
    cleanup();
    setTimeout(startTradingView, 5000);
  };

  console.log(`[TV] Subscribed to ${Object.keys(SYMBOLS).length} symbols`);
}

function cleanup() {
  try { markets.forEach(m => m.close()); } catch (_) {}
  try { tvClient.end(); } catch (_) {}
  markets = [];
  tvClient = null;
}

// ── Start ─────────────────────────────────────────────────────────────────────
httpServer.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════╗
║   AI Supply Chain — TradingView Bridge       ║
║   WebSocket: ws://localhost:${PORT}              ║
║   Press Ctrl+C to stop                       ║
╚══════════════════════════════════════════════╝
`);
  startTradingView();
});

process.on('SIGINT', () => {
  console.log('\n[Server] Shutting down…');
  cleanup();
  httpServer.close(() => process.exit(0));
});
