# 🔍 Complete Symbol Index & Codebase Directory

This file provides an index of all endpoints, Python functions, database operations, and frontend methods across the repository.

---

## 1. Backend REST Endpoints (`backend/main.py`)

| Endpoint | HTTP Method | Handler Function | Description |
| :--- | :--- | :--- | :--- |
| `/api/search` | `GET` | `search_tokens_endpoint` | Autocomplete & search tokens by ticker, name, or address (DexScreener API) |
| `/api/watchlist` | `GET` | `get_watchlist` | Retrieve all bookmarked tokens saved in SQLite Watchlist |
| `/api/token/{contract}` | `GET` | `get_token_intel` | Main token analysis with 3-tier caching (RAM -> SQLite -> Fresh) |
| `/api/token/{contract}/price` | `GET` | `get_token_price_only` | Fast price and liquidity lookup (DexScreener) |
| `/api/token/{contract}/holders` | `GET` | `get_top_holders_endpoint` | Top holders, total supply, total holders, and concentration |
| `/api/token/{contract}/traders` | `GET` | `get_top_traders_endpoint` | Top traders with volume, buy/sell counts, and estimated PnL |
| `/api/token/{contract}/refresh-tweets` | `POST` | `refresh_token_tweets` | User-triggered fresh scrape of X/Twitter and AI narrative |
| `/api/watchlist/{contract}/toggle` | `POST` | `toggle_watchlist_endpoint` | Toggle token watchlist state in SQLite |
| `/api/cache/stats` | `GET` | `get_cache_stats` | RAM cache hit/miss diagnostic counters |

---

## 2. Backend Services & Functions

### `backend/services/holders_traders.py`
- `evm_get_total_supply(chain, token_address)`: Executes `eth_call` for `totalSupply()` (`0x18160ddd`) and `decimals()` (`0x313ce567`).
- `solana_get_total_supply(mint_address)`: Calls Solana RPC `getTokenSupply`.
- `evm_get_top_holders(chain, token_address, ...)`: Scans `Transfer` event logs, aggregates balances, computes `% of supply`.
- `solana_get_top_holders(mint_address, ...)`: Queries `getTokenLargestAccounts` on Solana RPC.
- `evm_get_top_traders(chain, pair_address, ...)`: Scans Uniswap V2/V3 `Swap` logs, calculates volumes and estimated PnL.
- `fetch_top_holders(chain, contract_address, pair_address, price_usd)`: Unified router for holders and supply metrics.
- `fetch_top_traders(chain, contract_address, pair_address, price_usd)`: Unified router for DEX swap trader metrics.

### `backend/services/dexscreener.py`
- `fetch_token_data(contract_address)`: Fetches pairs from DexScreener, selects highest liquidity pair, extracts prices, taxes, and volume.

### `backend/services/social.py`
- `search_token_social(name, symbol, chain, ...)`: Coordinates SocialData Twitter search with DuckDuckGo fallback.

### `backend/services/summarizer.py`
- `summarize_narrative(name, symbol, token_data, social_data)`: Prompts Gemini 2.0 Flash to synthesize structured story, sentiment, hype level, and risk signals.

### `backend/services/search.py`
- `search_tokens(query, min_liquidity=500.0, limit=8)`: Searches tokens by ticker/name/address via DexScreener, filters low-liquidity spam, and caches results (60s TTL).

### `backend/services/cache.py`
- `TTLCache`: In-memory thread-safe dictionary with expiry timestamps.

---

## 3. Database Repositories (`backend/repositories/token_repository.py`)

- `db_get_token_intel(contract_address)`: Loads complete token record, narrative, tweets, and supply stats.
- `save_token_intel(contract_address, token_data, tweets, narrative, ...)`: Atomically upserts token and deduplicates tweets.
- `get_top_holders(token_id)`: Loads cached holders and supply metrics (`total_supply`, `total_holders`, `total_supply_held`, `total_supply_held_pct`).
- `save_top_holders(token_id, holders_data)`: Replaces holder snapshot and updates token supply columns in SQLite.
- `get_top_traders(token_id)`: Loads cached trader snapshot.
- `save_top_traders(token_id, traders_list)`: Replaces trader snapshot.
- `set_watchlist_status(contract_address, is_watchlist, ...)`: Toggles watchlist status.
- `get_watchlist_tokens()`: Retrieves all tokens marked in watchlist with their cached market stats.

---

## 4. Frontend Methods & DOM Mapping (`frontend/js/app.js`)

### Key Functions
- `populateData(data)`: Renders full token analysis and dispatches sub-component updates.
- `updateMarketMetricsOnly(token)`: Live updates price, market cap, FDV, total supply, volume, and taxes.
- `startAutoRefreshTimer()`: 10-second non-blocking countdown with Pause/Resume toggle.
- `loadWalletAnalytics(contract, chain, forceRefresh)`: Concurrently requests `/traders` and `/holders`.
- `renderHoldersTable(holders, chain, summaryData)`: Renders top holders table and the top supply summary bar.
- `renderTradersTable(traders, chain)`: Renders top traders table with PnL and buy/sell pills.
- `formatTokenSupply(amount)`: Compact token formatter (`1.00B`, `58.42M`, `12.50K`).
- `formatPrice(price)`: Adaptive currency formatter with scientific notation for sub-micro prices.

### Key DOM Element IDs
- Market Metrics: `#mcap`, `#fdv`, `#total-supply`, `#volume`, `#liquidity`, `#buy-tax`, `#sell-tax`.
- Holders Summary Bar: `#holders-summary-bar`, `#summary-total-supply`, `#summary-total-holders`, `#summary-supply-held-pct`, `#summary-supply-bar`.
- Containers & Tables: `#traders-table-body`, `#holders-table-body`, `#wallet-analytics-card`.
- Auto-refresh Controls: `#live-dot`, `#toggle-refresh-btn`, `#refresh-now-btn`.
