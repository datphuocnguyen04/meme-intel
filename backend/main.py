import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

from database import init_db
from repositories.token_repository import (
    get_token_intel as db_get_token_intel,
    save_token_intel,
    update_tweets_and_narrative,
    get_watchlist_tokens,
    set_watchlist_status,
    save_top_holders as db_save_top_holders,
    get_top_holders as db_get_top_holders,
    save_top_traders as db_save_top_traders,
    get_top_traders as db_get_top_traders,
)
from services.dexscreener import fetch_token_data
from services.social import search_token_social
from services.summarizer import summarize_narrative
from services.http_client import close_http_client
from services.cache import analysis_cache, price_cache
from services.holders_traders import fetch_top_holders, fetch_top_traders, get_explorer_url, CHAIN_EXPLORER
from services.search import search_tokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite database tables with WAL and RAM mmap
    init_db()
    yield
    # Shutdown: Clean up shared HTTP connection pool
    await close_http_client()


app = FastAPI(title="Memecoin Intel API", lifespan=lifespan)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/token/{contract_address}")
async def get_token_intel(contract_address: str):
    normalized_addr = contract_address.strip().lower()

    # 1. Tier 1: In-Memory RAM Cache (0.01ms pointer lookup)
    cached_analysis = await analysis_cache.get(normalized_addr)
    if cached_analysis:
        live_token_data = await fetch_token_data(contract_address)
        if live_token_data:
            cached_analysis["token"] = live_token_data
        cached_analysis["cached"] = True
        cached_analysis["cached_source"] = "ram"
        return cached_analysis

    # 2. Tier 2: SQLite Persistent Storage with WAL & mmap (< 1ms)
    db_record = db_get_token_intel(normalized_addr)
    if db_record and db_record.get("narrative"):
        # Token found in SQLite: fetch live price from DexScreener (0 API credits used)
        live_token_data = await fetch_token_data(contract_address)
        if not live_token_data:
            live_token_data = {
                "name": db_record.get("name"),
                "symbol": db_record.get("symbol"),
                "chain": db_record.get("chain"),
                "image_url": db_record.get("image_url"),
                "pair_address": db_record.get("pair_address"),
                "contract_address": db_record.get("contract_address"),
                "price_usd": "0",
            }

        if db_record.get("total_supply") and not live_token_data.get("total_supply"):
            live_token_data["total_supply"] = db_record.get("total_supply")

        result = {
            "token": live_token_data,
            "narrative": db_record["narrative"],
            "sources": [],
            "tweets": db_record["tweets"],
            "cached": True,
            "cached_source": "sqlite",
            "last_fetched_at": db_record.get("last_fetched_at", ""),
            "is_watchlist": db_record.get("is_watchlist", False),
        }

        # Keep RAM cache hot
        await analysis_cache.set(normalized_addr, result, ttl_seconds=600)
        return result

    # 3. Tier 3: Brand New Token -> Fetch DexScreener + SocialData X API + Gemini once
    token_data = await fetch_token_data(contract_address)
    if not token_data:
        raise HTTPException(status_code=404, detail="Token not found. Check contract address.")

    name = token_data.get("name", "Unknown")
    symbol = token_data.get("symbol", "Unknown")
    chain = token_data.get("chain", "Unknown")
    websites = token_data.get("websites", [])
    socials = token_data.get("socials", [])

    social_data = await search_token_social(
        name, symbol, chain,
        contract_address=contract_address,
        websites=websites,
        socials=socials,
    )

    narrative = await summarize_narrative(name, symbol, token_data, social_data)
    tweets = social_data.get("tweets", [])

    # Save to SQLite permanently so all future queries are free
    save_token_intel(contract_address, token_data, tweets, narrative)

    result = {
        "token": token_data,
        "narrative": narrative,
        "sources": social_data.get("results", []),
        "tweets": tweets,
        "cached": False,
        "cached_source": "fresh",
        "last_fetched_at": "Just now",
        "is_watchlist": False,
    }

    # Store in RAM Cache
    await analysis_cache.set(normalized_addr, result, ttl_seconds=600)
    return result


@app.post("/api/token/{contract_address}/refresh-tweets")
async def refresh_token_tweets(contract_address: str):
    """
    Explicit user-triggered refresh:
    Calls SocialData API for fresh tweets and updates Gemini AI narrative in SQLite.
    """
    normalized_addr = contract_address.strip().lower()

    token_data = await fetch_token_data(contract_address)
    if not token_data:
        raise HTTPException(status_code=404, detail="Token not found. Check contract address.")

    name = token_data.get("name", "Unknown")
    symbol = token_data.get("symbol", "Unknown")
    chain = token_data.get("chain", "Unknown")
    websites = token_data.get("websites", [])
    socials = token_data.get("socials", [])

    social_data = await search_token_social(
        name, symbol, chain,
        contract_address=contract_address,
        websites=websites,
        socials=socials,
    )

    narrative = await summarize_narrative(name, symbol, token_data, social_data)
    tweets = social_data.get("tweets", [])

    # Update SQLite database
    update_tweets_and_narrative(contract_address, tweets, narrative)

    result = {
        "token": token_data,
        "narrative": narrative,
        "sources": social_data.get("results", []),
        "tweets": tweets,
        "cached": False,
        "cached_source": "refreshed",
        "last_fetched_at": "Just now",
    }

    # Update RAM Cache
    await analysis_cache.set(normalized_addr, result, ttl_seconds=600)
    return result


@app.get("/api/token/{contract_address}/price")
async def get_token_price_only(contract_address: str):
    """Fast endpoint for live auto-refreshing prices using 10s RAM price cache."""
    token_data = await fetch_token_data(contract_address)
    if not token_data:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"token": token_data}


@app.get("/api/watchlist")
async def get_watchlist():
    """Retrieve all tokens saved in SQLite Watchlist."""
    items = get_watchlist_tokens()
    return {"watchlist": items}


@app.post("/api/watchlist/{contract_address}/toggle")
async def toggle_watchlist_endpoint(contract_address: str, payload: dict = Body(default={})):
    """Toggle or set watchlist status for a token in SQLite."""
    is_watchlist = payload.get("is_watchlist", True)
    token_data = payload.get("token")
    success = set_watchlist_status(contract_address, is_watchlist, token_data)
    return {"success": success, "is_watchlist": is_watchlist}


@app.get("/api/token/{contract_address}/holders")
async def get_top_holders_endpoint(contract_address: str, refresh: bool = False):
    """
    Returns top holders from on-chain RPC.
    Checks SQLite cache first unless refresh=True is specified.
    """
    normalized_addr = contract_address.strip().lower()
    db_record = db_get_token_intel(normalized_addr)
    
    token_data = await fetch_token_data(contract_address)
    if not token_data and not db_record:
        raise HTTPException(status_code=404, detail="Token not found. Check contract address.")

    token_id = db_record["token_id"] if db_record else None
    if not token_id and token_data:
        token_id = save_token_intel(contract_address, token_data, [], None)
        db_record = db_get_token_intel(normalized_addr)

    # 1. Check SQLite Cache if not explicitly refreshing
    if not refresh and token_id:
        cached_data = db_get_top_holders(token_id)
        if cached_data.get("holders"):
            chain = (token_data.get("chain") if token_data else db_record.get("chain", "")) or ""
            return {
                "holders": cached_data["holders"],
                "total_supply": cached_data.get("total_supply"),
                "total_holders": cached_data.get("total_holders"),
                "total_supply_held": cached_data.get("total_supply_held"),
                "total_supply_held_pct": cached_data.get("total_supply_held_pct"),
                "chain": chain,
                "explorer_url": CHAIN_EXPLORER.get(chain.lower(), ""),
                "fetched_at": cached_data.get("fetched_at"),
                "cached": True,
            }

    # 2. Fetch fresh on-chain RPC data
    chain = (token_data.get("chain") if token_data else (db_record.get("chain") if db_record else "")) or ""
    pair_address = (token_data.get("pair_address") if token_data else (db_record.get("pair_address") if db_record else "")) or ""
    try:
        price_usd = float(token_data.get("price_usd", 0) if token_data else 0)
    except (ValueError, TypeError):
        price_usd = 0.0

    holders_data = await fetch_top_holders(chain, contract_address, pair_address, price_usd)
    
    if isinstance(holders_data, dict):
        holders_list = holders_data.get("holders", [])
        total_supply = holders_data.get("total_supply")
        total_holders = holders_data.get("total_holders")
        total_supply_held = holders_data.get("total_supply_held")
        total_supply_held_pct = holders_data.get("total_supply_held_pct")
    else:
        holders_list = holders_data or []
        total_supply = None
        total_holders = len(holders_list)
        total_supply_held = None
        total_supply_held_pct = None

    if token_id and holders_data:
        db_save_top_holders(token_id, holders_data)

    return {
        "holders": holders_list,
        "total_supply": total_supply,
        "total_holders": total_holders,
        "total_supply_held": total_supply_held,
        "total_supply_held_pct": total_supply_held_pct,
        "chain": chain,
        "explorer_url": CHAIN_EXPLORER.get(chain.lower(), ""),
        "fetched_at": "Just now",
        "cached": False,
    }


@app.get("/api/token/{contract_address}/traders")
async def get_top_traders_endpoint(contract_address: str, refresh: bool = False):
    """
    Returns top traders with volume, txs, and estimated PnL from on-chain Swap events.
    Checks SQLite cache first unless refresh=True is specified.
    """
    normalized_addr = contract_address.strip().lower()
    db_record = db_get_token_intel(normalized_addr)
    
    token_data = await fetch_token_data(contract_address)
    if not token_data and not db_record:
        raise HTTPException(status_code=404, detail="Token not found. Check contract address.")

    token_id = db_record["token_id"] if db_record else None
    if not token_id and token_data:
        token_id = save_token_intel(contract_address, token_data, [], None)
        db_record = db_get_token_intel(normalized_addr)

    # 1. Check SQLite Cache if not explicitly refreshing
    if not refresh and token_id:
        cached_data = db_get_top_traders(token_id)
        if cached_data.get("traders"):
            chain = (token_data.get("chain") if token_data else db_record.get("chain", "")) or ""
            return {
                "traders": cached_data["traders"],
                "chain": chain,
                "explorer_url": CHAIN_EXPLORER.get(chain.lower(), ""),
                "fetched_at": cached_data.get("fetched_at"),
                "cached": True,
            }

    # 2. Fetch fresh on-chain Swap event data
    chain = (token_data.get("chain") if token_data else (db_record.get("chain") if db_record else "")) or ""
    pair_address = (token_data.get("pair_address") if token_data else (db_record.get("pair_address") if db_record else "")) or ""
    try:
        price_usd = float(token_data.get("price_usd", 0) if token_data else 0)
    except (ValueError, TypeError):
        price_usd = 0.0

    traders = await fetch_top_traders(chain, contract_address, pair_address, price_usd)
    
    if token_id and traders:
        db_save_top_traders(token_id, traders)

    return {
        "traders": traders,
        "chain": chain,
        "explorer_url": CHAIN_EXPLORER.get(chain.lower(), ""),
        "fetched_at": "Just now",
        "cached": False,
    }


@app.get("/api/search")
async def search_tokens_endpoint(q: str = ""):
    """
    Search tokens by name, ticker symbol, or address across DEXes.
    Returns deduplicated, liquidity-ranked token matches.
    """
    if not q or len(q.strip()) < 2:
        return {"results": []}
    results = await search_tokens(q.strip())
    return {"results": results}


@app.get("/api/cache/stats")
async def get_cache_stats():
    """Diagnostic endpoint to inspect RAM cache hits & performance."""
    return {
        "price_cache_hits": price_cache.hits,
        "price_cache_misses": price_cache.misses,
        "analysis_cache_hits": analysis_cache.hits,
        "analysis_cache_misses": analysis_cache.misses,
    }


# Ensure frontend directory exists for static file serving
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html not found, API is running"}
else:
    @app.get("/")
    async def root():
        return {"message": "Memecoin Intel API is running"}


if __name__ == "__main__":
    port = 8000
    print(f"Starting server on http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
