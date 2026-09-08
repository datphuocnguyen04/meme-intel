# 🤖 AGENTS.md — Memecoin Intel Agent Memory & Coding Guide

Welcome! This file serves as the **primary ground-truth memory** for AI coding assistants (Antigravity, Cursor, Claude Code, Windsurf, Aider, etc.) operating on this codebase.

---

## 1. Core Philosophy & Golden Rules

1. **ZERO 3rd-Party APIs for Wallet Analytics**:
   - ❌ **NEVER** use GeckoTerminal, Birdeye, Moralis, Alchemy SDK, or paid analytics APIs for holder balances or trader analytics.
   - ✅ **ALWAYS** use direct blockchain RPC nodes via standard JSON-RPC calls (`eth_call`, `eth_getLogs`, `getTokenSupply`, `getTokenLargestAccounts`).
2. **Supported Chains & Custom Networks**:
   - Fully supported EVM chains: **Ethereum**, **Base**, **BSC**, **Arbitrum**, **Polygon**, **Robinhood Chain** (Chain ID: `4663`), and **Ink Chain** (Chain ID: `57073`).
   - Supported non-EVM chains: **Solana**.
3. **Database Migrations Must Be Non-Destructive**:
   - When modifying SQLite schema in `backend/database.py`, **NEVER** drop existing tables or alter columns destructively.
   - Always query `PRAGMA table_info(<table_name>)` in `init_db()` and use `ALTER TABLE <table_name> ADD COLUMN ...` if the column is missing.
4. **Three-Tier Caching Hierarchy**:
   - **Tier 1**: In-memory RAM cache with TTL (`backend/services/cache.py`, 600s TTL).
   - **Tier 2**: SQLite persistent database (`backend/data/app.db`) with WAL mode and memory-mapped I/O (`< 1ms` retrieval).
   - **Tier 3**: Fresh on-chain RPC / DexScreener / SocialData fetch.
5. **Modular Frontend Preservation**:
   - **HTML**: `frontend/index.html` (markup structure only).
   - **CSS**: `frontend/css/styles.css` (visual styles and responsive design).
   - **JS**: `frontend/js/app.js` (DOM interactions and API client).
   - Do NOT introduce bulky frontend frameworks (React, Vue, Webpack) unless explicitly requested. Keep it lightweight, fast, and dependency-free.

---

## 2. Directory & Component Map

```
D:\meme-intel\
├── backend/
│   ├── data/
│   │   └── app.db                  # SQLite database (WAL mode enabled)
│   ├── repositories/
│   │   └── token_repository.py     # All SQLite CRUD queries for tokens, tweets, narratives, holders, traders
│   ├── services/
│   │   ├── cache.py                # In-memory RAM TTL cache
│   │   ├── dexscreener.py          # Real-time token market data (DexScreener API)
│   │   ├── holders_traders.py      # Direct on-chain RPC service (EVM & Solana)
│   │   ├── http_client.py          # Unified Async HTTP Client with timeouts
│   │   ├── social.py               # Social search aggregator (X API + DDG fallback)
│   │   ├── summarizer.py           # Gemini 2.0 Flash AI narrative synthesis
│   │   └── twitter_search.py       # SocialData API v2 integration for X/Twitter
│   ├── database.py                 # SQLite connection manager & schema migrations
│   ├── main.py                     # FastAPI REST API endpoints & static file serving
│   ├── requirements.txt            # Python dependencies (FastAPI, uvicorn, httpx, etc.)
│   └── .env                        # Environment variables (GEMINI_API_KEY, SOCIALDATA_API_KEY)
├── frontend/
│   ├── css/
│   │   └── styles.css              # Dark theme modern styles & wallet tables
│   ├── js/
│   │   └── app.js                  # Frontend application logic, auto-refresh, DOM updates
│   └── index.html                  # Main UI layout & responsive containers
├── docs/                           # Architectural diagrams, symbol indexes & ADRs
│   ├── ARCHITECTURE.md             # Detailed data flow and system diagrams
│   ├── SYMBOL_INDEX.md             # Complete directory of functions, routes & DOM IDs
│   ├── DEPENDENCY_GRAPH.md         # Component dependency and caller-callee graphs
│   └── DECISIONS.md                # Architectural Decision Records (ADRs)
├── scripts/
│   └── sync_agent_memory.py        # Automated AST tool to update symbol indexes
├── README.md                       # High-level project overview
└── AGENTS.md                       # This file (Agent Instructions & Invariants)
```

---

## 3. On-Chain RPC Node Specs

Defined in `backend/services/holders_traders.py`:

| Chain | Chain ID | RPC Endpoint | Explorer URL |
| :--- | :--- | :--- | :--- |
| **Robinhood** | `4663` | `https://rpc.robinhood.com` | `https://robinhoodchain.blockscout.com/address/` |
| **Ink** | `57073` | `https://rpc-gel.inkonchain.com` | `https://explorer.inkonchain.com/address/` |
| **Solana** | Mainnet | `https://api.mainnet-beta.solana.com` | `https://solscan.io/account/` |
| **Base** | `8453` | `https://mainnet.base.org` | `https://basescan.org/address/` |
| **Ethereum**| `1` | `https://eth.llamarpc.com` | `https://etherscan.io/address/` |
| **BSC** | `56` | `https://binance.llamarpc.com` | `https://bscscan.com/address/` |
| **Arbitrum**| `42161` | `https://arb1.arbitrum.io/rpc` | `https://arbiscan.io/address/` |
| **Polygon** | `137` | `https://polygon-rpc.com` | `https://polygonscan.com/address/` |

### Key Selectors & Event Topics
- **`totalSupply()`**: `0x18160ddd` (EVM `eth_call`)
- **`decimals()`**: `0x313ce567` (EVM `eth_call`)
- **ERC-20 `Transfer(address,address,uint256)`**: `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`
- **Uniswap V2 `Swap(address,uint,uint,uint,uint,address)`**: `0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822`
- **Uniswap V3 `Swap(address,address,int256,int256,uint160,uint128,int24)`**: `0xc42079f94a6350d7e6235f29174924f9b5fb35df81654de7b1c0fa5629da6fd`
- **Solana RPC**: `getTokenSupply`, `getTokenLargestAccounts`.

---

## 4. Database Schema Summary (`backend/database.py`)

- **`tokens`**: `id`, `contract_address`, `symbol`, `name`, `chain`, `image_url`, `pair_address`, `is_watchlist`, `total_supply`, `total_holders`, `total_supply_held`, `total_supply_held_pct`, `last_fetched_at`, `created_at`.
- **`narratives`**: `id`, `token_id`, `story`, `sentiment`, `hype_level`, `recent_buzz`, `low_confidence`, `created_at`.
- **`tweets`**: `id`, `token_id`, `tweet_id` (UNIQUE), `username`, `display_name`, `followers`, `verified`, `text`, `tweet_url`, `profile_image`, `likes`, `retweets`, `posted_at`, `fetched_at`.
- **`top_holders`**: `id`, `token_id`, `wallet_address`, `balance`, `percentage`, `value_usd`, `rank`, `source`, `fetched_at`.
- **`top_traders`**: `id`, `token_id`, `wallet_address`, `total_volume_usd`, `buy_count`, `sell_count`, `total_bought_usd`, `total_sold_usd`, `estimated_pnl_usd`, `estimated_pnl_pct`, `rank`, `fetched_at`.

---

## 5. API Endpoints (`backend/main.py`)

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/api/token/{contract}` | Main token intel: market metrics, AI narrative, tweets (caches to SQLite) |
| `GET` | `/api/token/{contract}/price` | Lightweight live price update (DexScreener API) |
| `GET` | `/api/token/{contract}/holders?refresh={bool}` | Top holders, total supply, total holders & concentration |
| `GET` | `/api/token/{contract}/traders?refresh={bool}` | Top DEX traders, volumes, buy/sell ratios & estimated PnL |
| `POST` | `/api/token/{contract}/refresh-tweets` | Explicit refresh of X/Twitter data and AI story |
| `POST` | `/api/watchlist/{contract}/toggle` | Toggle watchlist flag in SQLite |
| `GET` | `/api/cache/stats` | Diagnostic stats for in-memory cache hits/misses |

---

## 6. Developer & Testing Commands

From directory `D:\meme-intel\backend`:

```powershell
# 1. Check syntax across critical backend files
python -m py_compile main.py repositories/token_repository.py services/holders_traders.py database.py

# 2. Run backend server
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# 3. Test holders RPC endpoint directly (e.g. Waddles on Robinhood)
python -c "import urllib.request, json; print(json.dumps(json.loads(urllib.request.urlopen('http://127.0.0.1:8000/api/token/0xbb6ee7aa6d56266ccef3b1c0706bccce2f9a0cdd/holders').read()), indent=2))"

# 4. Sync / update symbol index and agent memory
python ../scripts/sync_agent_memory.py
```
