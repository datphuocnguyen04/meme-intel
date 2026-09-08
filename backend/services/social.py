import asyncio
import re
from typing import Dict, Any, List
from urllib.parse import urlparse
import httpx
from ddgs import DDGS
from services.twitter_search import search_twitter
from services.http_client import get_http_client


def extract_handle_from_url(url: str) -> str:
    """Extract username/handle from twitter or telegram URL."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path:
            handle = path.split("/")[0]
            handle = re.sub(r"[^a-zA-Z0-9_]", "", handle)
            return handle
    except Exception:
        pass
    return ""


async def fetch_website_preview(url: str) -> str:
    """Fetch website HTML using connection-pooled HTTP client and extract title, meta description, and body text."""
    try:
        client = get_http_client()
        resp = await client.get(url, timeout=3.5)
        if resp.status_code == 200:
            html = resp.text
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""

            desc_match = re.search(
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            if not desc_match:
                desc_match = re.search(
                    r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
                    html,
                    re.IGNORECASE,
                )
            desc = desc_match.group(1).strip() if desc_match else ""

            # Strip HTML tags for sample body text
            clean_body = re.sub(r"<[^>]+>", " ", html)
            clean_body = re.sub(r"\s+", " ", clean_body).strip()[:800]

            summary_parts = []
            if title:
                summary_parts.append(f"Title: {title}")
            if desc:
                summary_parts.append(f"Description: {desc}")
            if clean_body:
                summary_parts.append(f"Content excerpt: {clean_body}")

            return "\n".join(summary_parts)
    except Exception as e:
        print(f"Error fetching website {url}: {e}")
    return ""


async def search_token_social(
    token_name: str,
    token_symbol: str,
    chain: str,
    contract_address: str = "",
    websites: list = [],
    socials: list = [],
) -> Dict[str, Any]:
    queries = [
        f'"{token_name}" {chain} token crypto',
        f'"{token_name}" memecoin narrative origin story',
    ]

    # Add contract address query
    if contract_address:
        queries.append(f"{contract_address} token")

    # Extract handles from socials and add targeted queries
    extracted_handles = []
    primary_twitter_handle = ""
    for s in socials:
        s_url = s.get("url", "") if isinstance(s, dict) else str(s)
        s_type = s.get("type", "").lower() if isinstance(s, dict) else ""
        handle = extract_handle_from_url(s_url)
        if handle and len(handle) > 2 and handle.lower() not in ["home", "intent", "share", "channel"]:
            extracted_handles.append(handle)
            if "twitter" in s_type or "x.com" in s_url or "twitter.com" in s_url:
                if not primary_twitter_handle:
                    primary_twitter_handle = handle
            queries.append(f"{handle}")
            queries.append(f'"{token_name}" {handle}')

            # Check for company / brand hints in handles (e.g., amzn -> aws/amazon)
            if "amzn" in handle.lower():
                queries.append(f'"{token_name}" AWS duck')
                queries.append(f'"{token_name}" amazon developer')

    # Remove duplicates from queries list
    unique_queries = list(dict.fromkeys(queries))

    def run_searches():
        all_raw = []
        try:
            ddgs = DDGS()
            for q in unique_queries:
                try:
                    results = list(ddgs.text(q, max_results=5))
                    all_raw.extend(results)
                except Exception as e:
                    print(f"Search error for query '{q}': {e}")
        except Exception as e:
            print(f"DDGS init error: {e}")
        return all_raw

    # Prepare async tasks
    tasks = []

    # Task 1: DuckDuckGo Web Search
    tasks.append(asyncio.to_thread(run_searches))

    # Task 2: Twitter Search via SocialData API
    tasks.append(
        search_twitter(
            token_name=token_name,
            token_symbol=token_symbol,
            chain=chain,
            contract_address=contract_address,
            twitter_handle=primary_twitter_handle,
        )
    )

    # Task 3: Website previews
    website_urls = [
        (w.get("url", "") if isinstance(w, dict) else str(w))
        for w in websites
        if (w.get("url", "") if isinstance(w, dict) else str(w)).startswith("http")
    ]
    for w_url in website_urls:
        tasks.append(fetch_website_preview(w_url))

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        raw_web_results = results[0] if len(results) > 0 and isinstance(results[0], list) else []
        twitter_data = results[1] if len(results) > 1 and isinstance(results[1], dict) else {"tweets": [], "raw_text": ""}
        website_previews = results[2:] if len(results) > 2 else []

        # Deduplicate web search results by URL
        unique_urls = set()
        deduped_results = []
        raw_text_parts = []

        for item in raw_web_results:
            url = item.get("href", item.get("url", ""))
            title = item.get("title", "")
            body = item.get("body", item.get("snippet", ""))

            if url and url not in unique_urls:
                unique_urls.add(url)
                deduped_results.append({
                    "title": title,
                    "url": url,
                    "snippet": body,
                })
                raw_text_parts.append(f"{title}: {body}")

        # Build official context
        official_context_lines = []
        if websites:
            official_context_lines.append(
                "Official website(s): "
                + ", ".join(w.get("url", "") if isinstance(w, dict) else str(w) for w in websites)
            )
        if socials:
            official_context_lines.append(
                "Social channels: "
                + ", ".join(
                    f"{s.get('type','')}: {s.get('url','')}" if isinstance(s, dict) else str(s)
                    for s in socials
                )
            )

        # Add fetched website content
        for idx, preview in enumerate(website_previews):
            if isinstance(preview, str) and preview.strip():
                official_context_lines.append(f"\n[Official Website Content Preview #{idx+1}]:\n{preview}")

        official_context = "\n".join(official_context_lines)

        full_raw_text = ""
        if official_context:
            full_raw_text += "=== OFFICIAL TOKEN LINKS & ON-SITE CONTENT ===\n" + official_context + "\n\n"

        if twitter_data.get("raw_text") and twitter_data["raw_text"] != "No tweets found.":
            full_raw_text += "=== X/TWITTER LIVE TWEETS & COMMUNITY MENTIONS ===\n" + twitter_data["raw_text"] + "\n\n"

        full_raw_text += "=== WEB SEARCH & GENERAL BUZZ ===\n" + "\n---\n".join(raw_text_parts)

        return {
            "results": deduped_results,
            "raw_text": full_raw_text,
            "tweets": twitter_data.get("tweets", []),
        }

    except Exception as e:
        print(f"Error in social search: {e}")
        return {"results": [], "raw_text": "", "tweets": []}
