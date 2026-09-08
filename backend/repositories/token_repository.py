import json
import sqlite3
from typing import Optional, Dict, Any, List
from database import get_db_connection


def normalize_address(addr: str) -> str:
    return (addr or "").strip().lower()


def get_token_intel(contract_address: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve token, latest AI narrative, and stored tweets from SQLite.
    Returns None if token does not exist in local database.
    """
    norm_addr = normalize_address(contract_address)
    if not norm_addr:
        return None

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Fetch token
        cursor.execute(
            "SELECT * FROM tokens WHERE lower(contract_address) = ? LIMIT 1;",
            (norm_addr,)
        )
        token_row = cursor.fetchone()
        if not token_row:
            return None

        token_id = token_row["id"]

        # 2. Fetch latest narrative
        cursor.execute(
            "SELECT * FROM narratives WHERE token_id = ? ORDER BY id DESC LIMIT 1;",
            (token_id,)
        )
        narrative_row = cursor.fetchone()

        narrative_dict = None
        if narrative_row:
            buzz = []
            if narrative_row["recent_buzz"]:
                try:
                    buzz = json.loads(narrative_row["recent_buzz"])
                except Exception:
                    buzz = []

            narrative_dict = {
                "story": narrative_row["story"] or "",
                "sentiment": narrative_row["sentiment"] or "",
                "hype_level": narrative_row["hype_level"] or "Medium",
                "recent_buzz": buzz,
                "low_confidence": bool(narrative_row["low_confidence"]),
                "created_at": narrative_row["created_at"],
            }

        # 3. Fetch tweets sorted by engagement
        cursor.execute(
            """
            SELECT * FROM tweets 
            WHERE token_id = ? 
            ORDER BY (likes + retweets) DESC, id DESC 
            LIMIT 20;
            """,
            (token_id,)
        )
        tweet_rows = cursor.fetchall()

        tweets_list = []
        for t in tweet_rows:
            tweets_list.append({
                "username": t["username"] or "",
                "display_name": t["display_name"] or t["username"] or "",
                "followers": t["followers"] or 0,
                "verified": bool(t["verified"]),
                "text": t["text"] or "",
                "url": t["tweet_url"] or "",
                "profile_image": t["profile_image"] or "",
                "likes": t["likes"] or 0,
                "retweets": t["retweets"] or 0,
                "created_at": t["posted_at"] or "",
            })

        return {
            "token_id": token_id,
            "contract_address": token_row["contract_address"],
            "name": token_row["name"],
            "symbol": token_row["symbol"],
            "chain": token_row["chain"],
            "image_url": token_row["image_url"],
            "pair_address": token_row["pair_address"],
            "is_watchlist": bool(token_row["is_watchlist"]),
            "last_fetched_at": token_row["last_fetched_at"],
            "total_supply": token_row["total_supply"],
            "total_holders": token_row["total_holders"],
            "total_supply_held": token_row["total_supply_held"],
            "total_supply_held_pct": token_row["total_supply_held_pct"],
            "quote_symbol": token_row["quote_symbol"] if "quote_symbol" in token_row.keys() else "",
            "pair_label": token_row["pair_label"] if "pair_label" in token_row.keys() else "",
            "narrative": narrative_dict,
            "tweets": tweets_list,
        }


def save_token_intel(
    contract_address: str,
    token_data: Dict[str, Any],
    tweets: List[Dict[str, Any]],
    narrative: Optional[Dict[str, Any]],
    is_watchlist: bool = False,
) -> int:
    """
    Save fresh token intel into SQLite:
    - Upserts token metadata.
    - Deduplicates tweets using INSERT OR IGNORE on tweet_id.
    - Saves narrative version.
    """
    norm_addr = normalize_address(contract_address)
    name = token_data.get("name", "")
    symbol = token_data.get("symbol", "")
    quote_symbol = token_data.get("quote_symbol", "")
    pair_label = token_data.get("pair_label", "")
    chain = token_data.get("chain", "")
    image_url = token_data.get("image_url", "")
    pair_address = token_data.get("pair_address", "")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Upsert token
        cursor.execute(
            """
            INSERT INTO tokens (contract_address, symbol, name, quote_symbol, pair_label, chain, image_url, pair_address, is_watchlist, last_fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(contract_address) DO UPDATE SET
                symbol = excluded.symbol,
                name = excluded.name,
                quote_symbol = CASE WHEN excluded.quote_symbol != '' THEN excluded.quote_symbol ELSE tokens.quote_symbol END,
                pair_label = CASE WHEN excluded.pair_label != '' THEN excluded.pair_label ELSE tokens.pair_label END,
                chain = excluded.chain,
                image_url = CASE WHEN excluded.image_url != '' THEN excluded.image_url ELSE tokens.image_url END,
                pair_address = CASE WHEN excluded.pair_address != '' THEN excluded.pair_address ELSE tokens.pair_address END,
                last_fetched_at = datetime('now');
            """,
            (norm_addr, symbol, name, quote_symbol, pair_label, chain, image_url, pair_address, 1 if is_watchlist else 0)
        )

        cursor.execute("SELECT id FROM tokens WHERE lower(contract_address) = ?;", (norm_addr,))
        token_row = cursor.fetchone()
        token_id = token_row["id"]

        # 2. Insert tweets (skipping duplicates)
        for t in tweets:
            tweet_id = str(t.get("tweet_id") or t.get("id_str") or t.get("id") or t.get("url", ""))
            if not tweet_id:
                continue

            username = t.get("username", "")
            display_name = t.get("display_name", username)
            followers = t.get("followers", 0)
            verified = 1 if t.get("verified") else 0
            text = t.get("text", "")
            tweet_url = t.get("url", "")
            profile_image = t.get("profile_image", "")
            likes = t.get("likes", 0)
            retweets = t.get("retweets", 0)
            posted_at = t.get("created_at", "")

            cursor.execute(
                """
                INSERT OR IGNORE INTO tweets (
                    token_id, tweet_id, username, display_name, followers, verified,
                    text, tweet_url, profile_image, likes, retweets, posted_at, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'));
                """,
                (
                    token_id, tweet_id, username, display_name, followers, verified,
                    text, tweet_url, profile_image, likes, retweets, posted_at
                )
            )

        # 3. Insert narrative
        if narrative:
            story = narrative.get("story", "")
            sentiment = narrative.get("sentiment", "")
            hype_level = narrative.get("hype_level", "Medium")
            buzz_json = json.dumps(narrative.get("recent_buzz", []))
            low_conf = 1 if narrative.get("low_confidence") else 0

            cursor.execute(
                """
                INSERT INTO narratives (
                    token_id, story, sentiment, hype_level, recent_buzz, low_confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'));
                """,
                (token_id, story, sentiment, hype_level, buzz_json, low_conf)
            )

        conn.commit()
        return token_id


def update_tweets_and_narrative(
    contract_address: str,
    tweets: List[Dict[str, Any]],
    narrative: Optional[Dict[str, Any]],
) -> bool:
    """
    Used when user explicitly clicks 'Refresh X Tweets & Story':
    - Updates tokens.last_fetched_at.
    - Inserts new tweets.
    - Saves updated narrative version.
    """
    norm_addr = normalize_address(contract_address)
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM tokens WHERE lower(contract_address) = ?;", (norm_addr,))
        token_row = cursor.fetchone()
        if not token_row:
            return False

        token_id = token_row["id"]

        # Update last_fetched_at
        cursor.execute("UPDATE tokens SET last_fetched_at = datetime('now') WHERE id = ?;", (token_id,))

        # Insert new tweets
        for t in tweets:
            tweet_id = str(t.get("tweet_id") or t.get("id_str") or t.get("id") or t.get("url", ""))
            if not tweet_id:
                continue

            username = t.get("username", "")
            display_name = t.get("display_name", username)
            followers = t.get("followers", 0)
            verified = 1 if t.get("verified") else 0
            text = t.get("text", "")
            tweet_url = t.get("url", "")
            profile_image = t.get("profile_image", "")
            likes = t.get("likes", 0)
            retweets = t.get("retweets", 0)
            posted_at = t.get("created_at", "")

            cursor.execute(
                """
                INSERT OR IGNORE INTO tweets (
                    token_id, tweet_id, username, display_name, followers, verified,
                    text, tweet_url, profile_image, likes, retweets, posted_at, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'));
                """,
                (
                    token_id, tweet_id, username, display_name, followers, verified,
                    text, tweet_url, profile_image, likes, retweets, posted_at
                )
            )

        # Insert new narrative
        if narrative:
            story = narrative.get("story", "")
            sentiment = narrative.get("sentiment", "")
            hype_level = narrative.get("hype_level", "Medium")
            buzz_json = json.dumps(narrative.get("recent_buzz", []))
            low_conf = 1 if narrative.get("low_confidence") else 0

            cursor.execute(
                """
                INSERT INTO narratives (
                    token_id, story, sentiment, hype_level, recent_buzz, low_confidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'));
                """,
                (token_id, story, sentiment, hype_level, buzz_json, low_conf)
            )

        conn.commit()
        return True


def get_watchlist_tokens() -> List[Dict[str, Any]]:
    """Retrieve all tokens marked as in watchlist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT contract_address, symbol, name, quote_symbol, pair_label, chain, image_url, pair_address, last_fetched_at 
            FROM tokens 
            WHERE is_watchlist = 1 
            ORDER BY id DESC;
            """
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def set_watchlist_status(contract_address: str, is_watchlist: bool, token_data: Optional[Dict] = None) -> bool:
    """Add or remove token from SQLite watchlist."""
    norm_addr = normalize_address(contract_address)
    if not norm_addr:
        return False

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tokens WHERE lower(contract_address) = ?;", (norm_addr,))
        token_row = cursor.fetchone()

        quote_symbol = token_data.get("quote_symbol", "") if token_data else ""
        pair_label = token_data.get("pair_label", "") if token_data else ""

        if token_row:
            cursor.execute(
                """
                UPDATE tokens SET 
                    is_watchlist = ?,
                    quote_symbol = CASE WHEN ? != '' THEN ? ELSE quote_symbol END,
                    pair_label = CASE WHEN ? != '' THEN ? ELSE pair_label END
                WHERE id = ?;
                """,
                (1 if is_watchlist else 0, quote_symbol, quote_symbol, pair_label, pair_label, token_row["id"])
            )
        else:
            # Insert basic token entry if not present
            symbol = token_data.get("symbol", "") if token_data else ""
            name = token_data.get("name", "") if token_data else ""
            chain = token_data.get("chain", "") if token_data else ""
            image_url = token_data.get("image_url", "") if token_data else ""
            pair_address = token_data.get("pair_address", "") if token_data else ""

            cursor.execute(
                """
                INSERT INTO tokens (contract_address, symbol, name, quote_symbol, pair_label, chain, image_url, pair_address, is_watchlist)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (norm_addr, symbol, name, quote_symbol, pair_label, chain, image_url, pair_address, 1 if is_watchlist else 0)
            )

        conn.commit()
        return True


def save_top_holders(token_id: int, holders_data: Any) -> bool:
    """
    Replace all cached top holders and supply stats for a token with fresh blockchain RPC data.
    Deletes old rows and inserts the new snapshot atomically.
    """
    if isinstance(holders_data, dict):
        holders_list = holders_data.get("holders", [])
        total_supply = float(holders_data.get("total_supply") or 0.0)
        total_holders = int(holders_data.get("total_holders") or 0)
        total_supply_held = float(holders_data.get("total_supply_held") or 0.0)
        total_supply_held_pct = float(holders_data.get("total_supply_held_pct") or 0.0)
    else:
        holders_list = holders_data or []
        total_supply = 0.0
        total_holders = len(holders_list)
        total_supply_held = 0.0
        total_supply_held_pct = 0.0

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Update token supply stats in tokens table
        if total_supply > 0 or total_holders > 0:
            cursor.execute(
                """
                UPDATE tokens
                SET total_supply = ?, total_holders = ?, total_supply_held = ?, total_supply_held_pct = ?
                WHERE id = ?;
                """,
                (total_supply, total_holders, total_supply_held, total_supply_held_pct, token_id)
            )

        cursor.execute("DELETE FROM top_holders WHERE token_id = ?;", (token_id,))

        for h in holders_list:
            cursor.execute(
                """
                INSERT INTO top_holders (
                    token_id, wallet_address, balance, percentage, value_usd, rank, source, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'));
                """,
                (
                    token_id,
                    h.get("wallet_address", ""),
                    h.get("balance", "0"),
                    h.get("percentage", 0.0),
                    h.get("value_usd", 0.0),
                    h.get("rank", 0),
                    h.get("source", "rpc"),
                )
            )

        conn.commit()
        return True


def get_top_holders(token_id: int) -> Dict[str, Any]:
    """
    Retrieve cached top holders and supply metrics from SQLite.
    Returns dict with holders, total_supply, total_holders, total_supply_held, fetched_at.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Query token supply stats
        cursor.execute(
            "SELECT total_supply, total_holders, total_supply_held, total_supply_held_pct FROM tokens WHERE id = ?;",
            (token_id,)
        )
        token_row = cursor.fetchone()
        total_supply = float(token_row["total_supply"] or 0.0) if token_row else 0.0
        total_holders = int(token_row["total_holders"] or 0) if token_row else 0
        total_supply_held = float(token_row["total_supply_held"] or 0.0) if token_row else 0.0
        total_supply_held_pct = float(token_row["total_supply_held_pct"] or 0.0) if token_row else 0.0

        cursor.execute(
            "SELECT * FROM top_holders WHERE token_id = ? ORDER BY rank ASC;",
            (token_id,)
        )
        rows = cursor.fetchall()

        if not rows:
            return {
                "holders": [],
                "total_supply": total_supply,
                "total_holders": total_holders,
                "total_supply_held": total_supply_held,
                "total_supply_held_pct": total_supply_held_pct,
                "fetched_at": None,
            }

        holders = []
        for r in rows:
            holders.append({
                "wallet_address": r["wallet_address"],
                "balance": r["balance"],
                "percentage": r["percentage"],
                "value_usd": r["value_usd"],
                "rank": r["rank"],
                "source": r["source"],
            })

        return {
            "holders": holders,
            "total_supply": total_supply,
            "total_holders": total_holders,
            "total_supply_held": total_supply_held,
            "total_supply_held_pct": total_supply_held_pct,
            "fetched_at": rows[0]["fetched_at"],
        }


def save_top_traders(token_id: int, traders_list: List[Dict[str, Any]]) -> bool:
    """
    Replace all cached top traders for a token with fresh on-chain Swap event data.
    Deletes old rows and inserts the new snapshot atomically.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM top_traders WHERE token_id = ?;", (token_id,))

        for t in traders_list:
            cursor.execute(
                """
                INSERT INTO top_traders (
                    token_id, wallet_address, total_volume_usd, buy_count, sell_count,
                    total_bought_usd, total_sold_usd, estimated_pnl_usd, estimated_pnl_pct,
                    rank, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'));
                """,
                (
                    token_id,
                    t.get("wallet_address", ""),
                    t.get("total_volume_usd", 0.0),
                    t.get("buy_count", 0),
                    t.get("sell_count", 0),
                    t.get("total_bought_usd", 0.0),
                    t.get("total_sold_usd", 0.0),
                    t.get("estimated_pnl_usd", 0.0),
                    t.get("estimated_pnl_pct", 0.0),
                    t.get("rank", 0),
                )
            )

        conn.commit()
        return True


def get_top_traders(token_id: int) -> Dict[str, Any]:
    """
    Retrieve cached top traders from SQLite.
    Returns {"traders": [...], "fetched_at": "..."} or empty if none cached.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM top_traders WHERE token_id = ? ORDER BY rank ASC;",
            (token_id,)
        )
        rows = cursor.fetchall()

        if not rows:
            return {"traders": [], "fetched_at": None}

        traders = []
        for r in rows:
            traders.append({
                "wallet_address": r["wallet_address"],
                "total_volume_usd": r["total_volume_usd"],
                "buy_count": r["buy_count"],
                "sell_count": r["sell_count"],
                "total_bought_usd": r["total_bought_usd"],
                "total_sold_usd": r["total_sold_usd"],
                "estimated_pnl_usd": r["estimated_pnl_usd"],
                "estimated_pnl_pct": r["estimated_pnl_pct"],
                "rank": r["rank"],
            })

        return {
            "traders": traders,
            "fetched_at": rows[0]["fetched_at"],
        }
