# 📊 Code Dependency & Call Graph

This document details the call hierarchy and module dependencies across the backend and frontend.

---

## 1. Backend Module Hierarchy

```
backend/main.py
  ├── backend/database.py (init_db, get_db_connection)
  ├── backend/services/cache.py (analysis_cache, price_cache, search_cache)
  ├── backend/services/dexscreener.py (fetch_token_data)
  │     └── backend/services/http_client.py (get_http_client)
  ├── backend/services/search.py (search_tokens)
  │     ├── backend/services/http_client.py (get_http_client)
  │     └── backend/services/cache.py (search_cache)
  ├── backend/services/social.py (search_token_social)
  │     ├── backend/services/twitter_search.py (search_token_tweets)
  │     │     └── backend/services/http_client.py
  │     └── duckduckgo_search / ddgs (fallback)
  ├── backend/services/summarizer.py (summarize_narrative)
  │     └── google-genai (Gemini 2.0 Flash)
  ├── backend/services/holders_traders.py (fetch_top_holders, fetch_top_traders)
  │     └── httpx (Direct JSON-RPC)
  └── backend/repositories/token_repository.py
        └── backend/database.py (get_db_connection)
```

---

## 2. API Endpoint Call Sequences

### `/api/token/{contract_address}`
```
main.get_token_intel()
  ├── cache.get(normalized_addr)
  ├── token_repository.db_get_token_intel(normalized_addr)
  │     └── database.get_db_connection()
  ├── dexscreener.fetch_token_data(contract_address)
  ├── social.search_token_social(...)
  ├── summarizer.summarize_narrative(...)
  ├── token_repository.save_token_intel(...)
  └── cache.set(normalized_addr, result)
```

### `/api/token/{contract_address}/holders`
```
main.get_top_holders_endpoint()
  ├── token_repository.db_get_token_intel()
  ├── (if not refresh) token_repository.get_top_holders(token_id)
  ├── holders_traders.fetch_top_holders(chain, contract, pair, price)
  │     ├── holders_traders.evm_get_total_supply() OR solana_get_total_supply()
  │     └── holders_traders.evm_get_top_holders() OR solana_get_top_holders()
  └── token_repository.save_top_holders(token_id, holders_data)
```

### `/api/search?q={query}`
```
main.search_tokens_endpoint()
  └── search.search_tokens(query)
        ├── cache.search_cache.get(query)
        ├── http_client.get_http_client() -> DexScreener Search API
        └── cache.search_cache.set(query, results)
```

### `/api/watchlist`
```
main.get_watchlist()
  └── token_repository.get_watchlist_tokens()
        └── database.get_db_connection() (SELECT tokens WHERE is_watchlist = 1)
```
