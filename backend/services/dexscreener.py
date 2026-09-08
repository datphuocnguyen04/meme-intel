import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from services.http_client import get_http_client
from services.cache import price_cache

async def fetch_token_tax(chain: str, contract_address: str) -> tuple:
    """Fetch buy and sell tax via GoPlus Token Security API using connection-pooled HTTP client."""
    if not chain or not contract_address:
        return "0%", "0%"
    
    chain_lower = chain.lower()
    if chain_lower in ["solana", "sol"]:
        return "0%", "0%"

    chain_map = {
        "ethereum": "1", "eth": "1", "bsc": "56", "bnb": "56",
        "base": "8453", "arbitrum": "42161", "polygon": "137",
        "avalanche": "43114", "optimism": "10", "blast": "81457",
        "linea": "59144", "cronos": "25", "fantom": "250", "zksync": "324"
    }
    chain_id = chain_map.get(chain_lower)
    if not chain_id:
        return "0%", "0%"

    try:
        url = f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={contract_address}"
        client = get_http_client()
        resp = await client.get(url, timeout=3.0)
        if resp.status_code == 200:
            result = resp.json().get("result", {})
            token_sec = result.get(contract_address.lower(), {}) or result.get(contract_address, {})
            if token_sec:
                raw_buy = token_sec.get("buy_tax")
                raw_sell = token_sec.get("sell_tax")
                is_honeypot = token_sec.get("is_honeypot") == "1"

                buy_pct = "0%"
                sell_pct = "0%"

                if raw_buy is not None and raw_buy != "":
                    try:
                        b_val = float(raw_buy)
                        buy_pct = f"{b_val * 100:.1f}%" if b_val < 1.0 and b_val > 0 else f"{b_val:.1f}%" if b_val > 0 else "0%"
                    except ValueError:
                        buy_pct = str(raw_buy)

                if raw_sell is not None and raw_sell != "":
                    try:
                        s_val = float(raw_sell)
                        sell_pct = f"{s_val * 100:.1f}%" if s_val < 1.0 and s_val > 0 else f"{s_val:.1f}%" if s_val > 0 else "0%"
                    except ValueError:
                        sell_pct = str(raw_sell)

                if is_honeypot:
                    sell_pct = "100% (HONEYPOT)"

                return buy_pct, sell_pct
    except Exception as e:
        print(f"Error fetching token tax from GoPlus: {e}")

    return "0%", "0%"

async def fetch_token_data(contract_address: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch token market data from DexScreener + GoPlus.
    Uses in-memory RAM caching (10s TTL) and persistent HTTP connection pooling.
    """
    normalized_addr = contract_address.strip().lower()
    
    # 1. Check RAM Cache
    if use_cache:
        cached = await price_cache.get(normalized_addr)
        if cached:
            return cached

    url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address.strip()}"
    
    try:
        client = get_http_client()
        response = await client.get(url, timeout=6.0)
        response.raise_for_status()
        data = response.json()
        
        pairs = data.get("pairs")
        if not pairs:
            return None
        
        # Sort by liquidity.usd descending to get the highest liquidity pair
        def get_liquidity(pair):
            try:
                return float(pair.get("liquidity", {}).get("usd", 0))
            except (ValueError, TypeError):
                return 0.0

        best_pair = max(pairs, key=get_liquidity)
        
        # Extract basic data
        name = best_pair.get("baseToken", {}).get("name")
        symbol = best_pair.get("baseToken", {}).get("symbol")
        chain = best_pair.get("chainId")
        price_usd = best_pair.get("priceUsd")
        
        quote_token = best_pair.get("quoteToken") or {}
        quote_symbol = quote_token.get("symbol") or ""
        pair_label = f"{symbol}/{quote_symbol}" if (symbol and quote_symbol) else (symbol or "")
        
        # Market Cap or FDV
        market_cap = best_pair.get("marketCap") or best_pair.get("fdv")
        fdv = best_pair.get("fdv")
        
        volume_24h = best_pair.get("volume", {}).get("h24")
        liquidity_usd = best_pair.get("liquidity", {}).get("usd")
        
        price_change = {
            "m5": best_pair.get("priceChange", {}).get("m5"),
            "h1": best_pair.get("priceChange", {}).get("h1"),
            "h6": best_pair.get("priceChange", {}).get("h6"),
            "h24": best_pair.get("priceChange", {}).get("h24"),
        }
        
        txns_24h = {
            "buys": best_pair.get("txns", {}).get("h24", {}).get("buys"),
            "sells": best_pair.get("txns", {}).get("h24", {}).get("sells")
        }
        
        pair_url = best_pair.get("url")
        pair_address = best_pair.get("pairAddress")
        dex = best_pair.get("dexId")
        
        created_at_ms = best_pair.get("pairCreatedAt")
        created_at = None
        if created_at_ms:
            created_at = datetime.fromtimestamp(created_at_ms / 1000.0, tz=timezone.utc).isoformat()
            
        info = best_pair.get("info", {})
        image_url = info.get("imageUrl")
        websites = info.get("websites", [])
        socials = info.get("socials", [])

        # Fetch buy/sell tax
        buy_tax, sell_tax = await fetch_token_tax(chain, contract_address.strip())
        
        result = {
            "name": name,
            "symbol": symbol,
            "quote_symbol": quote_symbol,
            "pair_label": pair_label,
            "chain": chain,
            "price_usd": price_usd,
            "market_cap": market_cap,
            "fdv": fdv,
            "volume_24h": volume_24h,
            "liquidity_usd": liquidity_usd,
            "price_change": price_change,
            "txns_24h": txns_24h,
            "pair_url": pair_url,
            "pair_address": pair_address,
            "contract_address": best_pair.get("baseToken", {}).get("address") or contract_address.strip(),
            "dex": dex,
            "created_at": created_at,
            "image_url": image_url,
            "websites": websites,
            "socials": socials,
            "buy_tax": buy_tax,
            "sell_tax": sell_tax
        }

        # Save to RAM Cache (10s TTL)
        await price_cache.set(normalized_addr, result, ttl_seconds=10)
        
        return result
        
    except (httpx.RequestError, ValueError) as e:
        print(f"Error fetching DexScreener data: {e}")
        return None
