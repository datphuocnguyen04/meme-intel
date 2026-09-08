import time
from typing import List, Dict, Any, Optional
from services.http_client import get_http_client
from services.cache import InMemoryTTLCache

# 60-second TTL cache for search queries
search_cache = InMemoryTTLCache(default_ttl_seconds=60, max_items=5000)

async def search_tokens(query: str, min_liquidity: float = 500.0, limit: int = 8) -> List[Dict[str, Any]]:
    """
    Search tokens by name, symbol, or contract address via DexScreener search API.
    - Deduplicates multiple liquidity pools by baseToken address.
    - Retains the pool with the highest USD liquidity.
    - Filters out spam/dead tokens with liquidity < min_liquidity.
    - Sorts descending by liquidity.
    - Caches results for 60 seconds.
    """
    q = (query or '').strip()
    if not q or len(q) < 2:
        return []

    cache_key = q.lower()
    cached = await search_cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"https://api.dexscreener.com/latest/dex/search?q={q}"
    
    try:
        client = get_http_client()
        resp = await client.get(url, timeout=6.0)
        if resp.status_code != 200:
            return []
        
        data = resp.json()
        pairs = data.get("pairs") or []
        if not pairs:
            await search_cache.set(cache_key, [], ttl_seconds=30)
            return []

        # Deduplicate pairs by token address, keeping the highest liquidity pair
        best_token_pairs: Dict[str, Any] = {}

        for p in pairs:
            base_token = p.get("baseToken") or {}
            token_addr = (base_token.get("address") or "").strip().lower()
            if not token_addr:
                continue

            # Extract liquidity USD
            try:
                liq_usd = float(p.get("liquidity", {}).get("usd", 0) or 0)
            except (ValueError, TypeError):
                liq_usd = 0.0

            # Filter out zero or spam liquidity if it doesn't meet threshold
            # (unless it's the only result or an exact contract address search)
            if liq_usd < min_liquidity and len(pairs) > 5:
                continue

            if token_addr not in best_token_pairs:
                best_token_pairs[token_addr] = (liq_usd, p)
            else:
                existing_liq, _ = best_token_pairs[token_addr]
                if liq_usd > existing_liq:
                    best_token_pairs[token_addr] = (liq_usd, p)

        # Sort tokens by liquidity descending
        sorted_tokens = sorted(best_token_pairs.values(), key=lambda item: item[0], reverse=True)

        results: List[Dict[str, Any]] = []
        for liq_usd, p in sorted_tokens[:limit]:
            base_token = p.get("baseToken") or {}
            quote_token = p.get("quoteToken") or {}
            quote_symbol = quote_token.get("symbol", "")
            base_sym = base_token.get("symbol", "???")
            pair_label = f"{base_sym}/{quote_symbol}" if quote_symbol else base_sym
            info = p.get("info") or {}
            price_change = p.get("priceChange") or {}

            results.append({
                "address": base_token.get("address", ""),
                "name": base_token.get("name", "Unknown"),
                "symbol": base_sym,
                "quote_symbol": quote_symbol,
                "pair_label": pair_label,
                "chain": p.get("chainId", "unknown"),
                "price_usd": p.get("priceUsd", "0"),
                "price_change_24h": price_change.get("h24"),
                "liquidity_usd": liq_usd,
                "fdv": p.get("fdv") or p.get("marketCap"),
                "pair_address": p.get("pairAddress", ""),
                "image_url": info.get("imageUrl") or "",
            })

        await search_cache.set(cache_key, results, ttl_seconds=60)
        return results
    except Exception as e:
        print(f"Error in search_tokens: {e}")
        return []
