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
  LITE: 'NASDAQ:LITE',  // Lumentum — optical components peer of COHR
  HPE:  'NYSE:HPE',     // Hewlett Packard Enterprise — AI servers + Cray
  // ── Robotics chart additions ───────────────────────────────────────────
  RRX:  'NYSE:RRX',     // Regal Rexnord — precision gearboxes
  TKR:  'NYSE:TKR',     // Timken — bearings
  AME:  'NYSE:AME',     // Ametek — precision motion
  QCOM: 'NASDAQ:QCOM',  // Qualcomm — Dragonwing robotics chips
  TXN:  'NASDAQ:TXN',   // Texas Instruments — motor control ICs
  ADI:  'NASDAQ:ADI',   // Analog Devices — IMU/MEMS
  CGNX: 'NASDAQ:CGNX',  // Cognex — machine vision
  OUST: 'NASDAQ:OUST',  // Ouster — LiDAR
  AEVA: 'NASDAQ:AEVA',  // Aeva — FMCW LiDAR
  TDY:  'NYSE:TDY',     // Teledyne — FLIR thermal/vision
  ROK:  'NYSE:ROK',     // Rockwell Automation
  EMR:  'NYSE:EMR',     // Emerson Electric
  ABB:  'OTC:ABBNY',    // ABB Ltd — US ADR trades as ABBNY on OTC
  TER:  'NASDAQ:TER',   // Teradyne — Universal Robots + MiR
  SYM:  'NASDAQ:SYM',   // Symbotic — warehouse robotics
  ISRG: 'NASDAQ:ISRG',  // Intuitive Surgical — da Vinci
  MDT:  'NYSE:MDT',     // Medtronic — Hugo RAS
  SYK:  'NYSE:SYK',     // Stryker — Mako orthopedic
  TSLA: 'NASDAQ:TSLA',  // Tesla — Optimus humanoid
  AVAV: 'NASDAQ:AVAV',  // AeroVironment — drones
  WMT:  'NASDAQ:WMT',   // Walmart — Symbotic deployment
  // ── Defense chart additions ────────────────────────────────────────────
  KO:   'NYSE:KO',      // Coca-Cola
  PEP:  'NASDAQ:PEP',   // PepsiCo
  PG:   'NYSE:PG',      // Procter & Gamble
  CL:   'NYSE:CL',      // Colgate-Palmolive
  COST: 'NASDAQ:COST',  // Costco
  JNJ:  'NYSE:JNJ',     // Johnson & Johnson
  LLY:  'NYSE:LLY',     // Eli Lilly
  UNH:  'NYSE:UNH',     // UnitedHealth
  ABT:  'NYSE:ABT',     // Abbott Laboratories
  NEE:  'NYSE:NEE',     // NextEra Energy
  DUK:  'NYSE:DUK',     // Duke Energy
  SO:   'NYSE:SO',      // Southern Company
  AWK:  'NYSE:AWK',     // American Water Works
  VZ:   'NYSE:VZ',      // Verizon
  T:    'NYSE:T',       // AT&T
  AMT:  'NYSE:AMT',     // American Tower
  MCD:  'NYSE:MCD',     // McDonald's
  DG:   'NYSE:DG',      // Dollar General
  WM:   'NYSE:WM',      // Waste Management
  YUM:  'NYSE:YUM',     // Yum! Brands
  // ── Space chart additions ──────────────────────────────────────────────
  // L0 上游元器件
  HXL:  'NYSE:HXL',     // Hexcel — 碳纤维复合材料
  MOG:  'NYSE:MOG.A',   // Moog Inc Class A — 精密执行器/阀门
  MRCY: 'NASDAQ:MRCY',  // Mercury Systems — 抗辐射芯片
  RDW:  'NYSE:RDW',     // Redwire — 太阳能阵列/在轨制造
  // L1 整星与火箭
  SPCX: 'NASDAQ:SPCX',  // SpaceX — 2026.6 IPO
  RKLB: 'NASDAQ:RKLB',  // Rocket Lab
  LMT:  'NYSE:LMT',     // Lockheed Martin
  NOC:  'NYSE:NOC',     // Northrop Grumman
  BA:   'NYSE:BA',      // Boeing
  // L2 运营商
  ASTS: 'NASDAQ:ASTS',  // AST SpaceMobile
  IRDM: 'NASDAQ:IRDM',  // Iridium
  GSAT: 'NASDAQ:GSAT',  // Globalstar
  VSAT: 'NASDAQ:VSAT',  // Viasat
  PL:   'NYSE:PL',      // Planet Labs
  BKSY: 'NYSE:BKSY',    // BlackSky
  // L3 终端客户
  AAPL: 'NASDAQ:AAPL',  // Apple
  TMUS: 'NASDAQ:TMUS',  // T-Mobile
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
let lastDataAt = Date.now();
let updateCount = 0;

function startTradingView() {
  console.log('[TV] Connecting to TradingView…');
  lastDataAt = Date.now();

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

      // Prefer TradingView's own ch/chp fields — they always reflect today's session
      // baseline (TradingView updates the reference price each day). Falling back to
      // manual computation only when the native fields are absent.
      const change    = data.ch  ?? ((price != null && prevClose != null) ? price - prevClose : null);
      const changePct = data.chp ?? ((price != null && prevClose != null && prevClose !== 0)
        ? (price - prevClose) / prevClose * 100
        : null);

      if (price == null) return;

      // Skip identical updates (same price as cached) to reduce noise
      const cached = quoteCache[ticker];
      const priceChanged = !cached || cached.price !== price;

      const quote = { ticker, price, change, changePct, volume, high, low, prevClose };
      quoteCache[ticker] = quote;
      lastDataAt = Date.now();
      updateCount++;

      if (priceChanged) {
        broadcast({ type: 'quote', ...quote });
        process.stdout.write(
          `\n[${new Date().toISOString().slice(11,19)}] [${ticker.padEnd(5)}] $${price.toFixed(2).padStart(10)}  ${(changePct ?? 0) >= 0 ? '+' : ''}${(changePct ?? 0).toFixed(2)}%`
        );
      }
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

// ── Stale-connection watchdog ────────────────────────────────────────────────
// TradingView's quote session sometimes goes silent without throwing an error.
// If no data for 60s, force a reconnect to restore the live feed.
setInterval(() => {
  const silent = (Date.now() - lastDataAt) / 1000;
  if (silent > 60) {
    console.log(`\n[TV] No data for ${silent.toFixed(0)}s — forcing reconnect (updates so far: ${updateCount})`);
    cleanup();
    lastDataAt = Date.now();   // prevent immediate re-trigger
    updateCount = 0;
    setTimeout(startTradingView, 1000);
  }
}, 30000);

// Periodic status log every 60s so we can see the feed is alive
setInterval(() => {
  const silent = (Date.now() - lastDataAt) / 1000;
  console.log(`\n[STATUS] updates=${updateCount}, silent=${silent.toFixed(0)}s, clients=${wss.clients.size}, cached=${Object.keys(quoteCache).length}`);
}, 60000);

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
