# 🧠 Memecoin Intel

> **Real-time memecoin intelligence engine**: Direct on-chain blockchain RPC analysis, verified X/Twitter community sentiment, live price streaming, and Gemini AI narrative synthesis — with zero 3rd-party wallet APIs.

---

## 🚀 Key Features

- **Direct Blockchain RPC Analytics (0 Paid APIs)**:
  - Queries exact token `totalSupply()`, active holders count, and concentration percentage.
  - Analyzes on-chain DEX `Swap` events (Uniswap V2/V3) to compute trader volume, buy/sell ratios, and estimated PnL.
  - Native multi-chain support: **Robinhood Chain (4663)**, **Ink Chain (57073)**, **Solana**, **Base**, **Ethereum**, **BSC**, **Arbitrum**, and **Polygon**.
- **Real-Time Market Metrics & 10s Live Auto-Refresh**:
  - Live price, Market Cap, FDV, Total Supply, 24h Volume, Liquidity, and Buy/Sell taxes.
  - Non-blocking auto-refresh timer with price green/red flash animations and Pause/Resume controls.
- **AI Narrative & Social Sentiment**:
  - Fetches top tweets from verified creators via SocialData X API.
  - Summarizes token lore, community buzz, hype level, and risk signals via Google Gemini 2.0 Flash.
- **Sub-Millisecond Dual-Tier Cache**:
  - Tier 1: In-memory TTL RAM cache.
  - Tier 2: SQLite database (`backend/data/app.db`) in WAL mode with non-destructive PRAGMA migrations.
- **Local Watchlist**:
  - Pin favorite tokens to monitor live price fluctuations and quick-load analysis.

---

## 🛠️ Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment
Create `.env` inside `backend/`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
SOCIALDATA_API_KEY=your_socialdata_key_here
```

### 3. Run the Server
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Open in Browser
Visit **http://localhost:8000**. Try searching:
- **Robinhood Chain**: `0xbb6ee7aa6d56266ccef3b1c0706bccce2f9a0cdd` ($WADDLES)
- **Ink Chain**: `0x19a00885e35fa8ebae760773d2a7536d5fe00130` ($ICAT)
- **Solana**: `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263` ($BONK)

---

## 📚 Agent & Developer Documentation

For complete architectural flows, symbol directories, and coding conventions:
- [AGENTS.md](AGENTS.md) — Agent memory, golden rules, and invariants.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — End-to-end data flow and RPC specs.
- [docs/SYMBOL_INDEX.md](docs/SYMBOL_INDEX.md) — Exhaustive directory of functions, routes, and DOM IDs.
- [docs/DEPENDENCY_GRAPH.md](docs/DEPENDENCY_GRAPH.md) — Component call hierarchy.
- [docs/DECISIONS.md](docs/DECISIONS.md) — Architectural Decision Records (ADRs).
