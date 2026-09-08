import asyncio
import httpx
import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from services.http_client import get_http_client

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)


async def search_twitter(
    token_name: str,
    token_symbol: str,
    chain: str,
    contract_address: str = "",
    twitter_handle: str = "",
) -> Dict[str, Any]:
    """
    Search X/Twitter for tweets about a specific memecoin using the SocialData.tools API.
    Uses connection pooling to minimize HTTP handshake latency.
    """
    api_key = os.environ.get("SOCIALDATA_API_KEY", "")
    if not api_key:
        return {"tweets": [], "raw_text": ""}

    base_url = "https://api.socialdata.tools/twitter/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    # Build targeted search queries
    queries = []

    # 1. Cashtag search — crypto traders use $SYMBOL
    if token_symbol:
        queries.append(f"${token_symbol} crypto")

    # 2. Contract address — finds exact discussions about this token
    if contract_address:
        queries.append(contract_address)

    # 3. Token name + chain
    if token_name and chain:
        queries.append(f'"{token_name}" {chain} token')

    # 4. Official handle's recent tweets
    if twitter_handle:
        queries.append(f"from:{twitter_handle}")

    async def run_single_search(query: str) -> list:
        """Run a single Twitter search query using shared pooled client."""
        try:
            params = {"query": query, "type": "Latest"}
            client = get_http_client()
            resp = await client.get(base_url, headers=headers, params=params, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tweets", [])
            elif resp.status_code == 402:
                print(f"SocialData API: Insufficient balance (402) for query: {query}")
                return []
            elif resp.status_code == 429:
                print(f"SocialData API: Rate limited (429) for query: {query}")
                return []
            else:
                return []
        except Exception as e:
            print(f"Twitter search error for '{query}': {e}")
            return []

    # Run all queries in parallel
    try:
        results = await asyncio.gather(
            *[run_single_search(q) for q in queries],
            return_exceptions=True
        )
    except Exception as e:
        print(f"Twitter search gather error: {e}")
        return {"tweets": [], "raw_text": ""}

    # Flatten and deduplicate by tweet ID
    seen_ids = set()
    all_tweets = []

    for result in results:
        if isinstance(result, Exception) or not isinstance(result, list):
            continue
        for tweet in result:
            tweet_id = tweet.get("id_str") or tweet.get("id")
            if tweet_id and tweet_id not in seen_ids:
                seen_ids.add(tweet_id)
                all_tweets.append(tweet)

    # Sort by engagement (likes + retweets) descending
    def get_engagement(t):
        likes = t.get("favorite_count", 0) or 0
        rts = t.get("retweet_count", 0) or 0
        return likes + rts

    all_tweets.sort(key=get_engagement, reverse=True)

    # Take top 15 most engaging tweets
    top_tweets = all_tweets[:15]

    formatted_tweets = []
    raw_text_parts = []

    for t in top_tweets:
        user = t.get("user", {})
        username = user.get("screen_name", "unknown")
        display_name = user.get("name", username)
        followers = user.get("followers_count", 0)
        verified = user.get("is_blue_verified", False) or user.get("verified", False)
        text = t.get("full_text") or t.get("text", "")
        likes = t.get("favorite_count", 0) or 0
        retweets = t.get("retweet_count", 0) or 0
        created_at = t.get("created_at", "")
        tweet_id = t.get("id_str") or str(t.get("id", ""))
        profile_image = user.get("profile_image_url_https", "")

        tweet_url = f"https://x.com/{username}/status/{tweet_id}" if tweet_id else ""

        formatted_tweets.append({
            "username": username,
            "display_name": display_name,
            "followers": followers,
            "verified": verified,
            "text": text[:500],
            "likes": likes,
            "retweets": retweets,
            "created_at": created_at,
            "url": tweet_url,
            "profile_image": profile_image,
        })

        verified_tag = " [VERIFIED]" if verified else ""
        raw_text_parts.append(
            f"@{username}{verified_tag} ({followers} followers) — "
            f"❤️{likes} 🔁{retweets}: {text[:300]}"
        )

    raw_text = "\n---\n".join(raw_text_parts) if raw_text_parts else "No tweets found."

    return {
        "tweets": formatted_tweets,
        "raw_text": raw_text,
    }
