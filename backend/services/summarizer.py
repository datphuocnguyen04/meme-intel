import os
import json
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv
from google import genai

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

def _get_fallback_summary() -> Dict[str, Any]:
    return {
        "hype_level": "Medium",
        "story": "AI summary unavailable — set GEMINI_API_KEY",
        "recent_buzz": ["Data could not be fetched."],
        "sentiment": "Unknown",
        "risk_signals": ["API Key missing"],
        "tags": []
    }

async def summarize_narrative(token_name: str, token_symbol: str, token_data: Dict[str, Any], social_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return _get_fallback_summary()
        
    contract_address = token_data.get("pair_address", "")
    chain = token_data.get("chain", "unknown")
    websites = token_data.get("websites", [])
    socials = token_data.get("socials", [])

    official_links = ""
    if websites:
        official_links += "Official website(s): " + ", ".join(
            w.get("url", "") if isinstance(w, dict) else str(w) for w in websites
        ) + "\n"
    if socials:
        official_links += "Social accounts: " + ", ".join(
            f"{s.get('type','')}: {s.get('url','')}" if isinstance(s, dict) else str(s)
            for s in socials
        ) + "\n"

    prompt = f"""You are an elite crypto research analyst specializing in memecoin narratives, developer culture, viral X/Twitter threads, and market sentiment.
Your goal is to extract and deliver an accurate, well-researched narrative summary for the token based on live web and X data.

CORE DIRECTIVES:
1. TARGET ASSET: Token "{token_name}" (${token_symbol}) on {chain} (Contract: {contract_address}).
2. LORE & X NARRATIVE SYNTHESIS:
   - Carefully review the "=== X/TWITTER LIVE TWEETS & COMMUNITY MENTIONS ===" and official links.
   - Give high weight to tweets from verified creators, project founders, or viral threads with high likes/retweets.
   - For developer/tech memecoins (e.g. AWS duck mascots, viral X developer threads, ASCII art, coding inside jokes), clearly highlight that developer community lore and origin.
   - Filter out and ignore noise from unrelated coins or projects that simply happen to share a common word.
3. CONCISE & AUTHORITATIVE: Provide a crisp, engaging summary directly explaining what this coin represents without disclaimer boilerplate.

TOKEN DATA:
- Name: {token_name}
- Symbol: ${token_symbol}
- Chain: {chain}
- Contract: {contract_address}
- Price USD: {token_data.get('price_usd')}
- Market Cap: {token_data.get('market_cap')}
{official_links}

EVIDENCE & RESEARCH SNIPPETS (WEB + X/TWITTER):
{social_data.get('raw_text', 'No social data available.')}

Respond ONLY with a valid JSON object matching these fields:
- hype_level: "Low", "Medium", "High", or "Extreme"
- story: 1-2 concise sentences explaining the authentic origin, theme, and cultural narrative of THIS coin.
- recent_buzz: 3-5 bullet points covering recent milestones, viral tweets/threads, community campaigns, or catalyst events.
- sentiment: 1-2 sentences on community sentiment, trader excitement, and social momentum.
- risk_signals: List of specific risks (e.g. liquidity depth, volatility, market cap size, ticker collisions).
- tags: 3-6 relevant tags (e.g. ["AWS Duck", "Developer Meme", "ASCII Lore", "Robinhood Chain", "Tech Culture"]).
- low_confidence: true only if there is genuinely no verifiable information found for this asset, otherwise false.

Return pure JSON without any markdown code fences.
"""
    
    def call_gemini():
        client = genai.Client(api_key=api_key)
        for model_name in ['gemini-3.6-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                print(f"Failed with {model_name}: {e}")
                continue
            
        raise RuntimeError("No compatible Gemini model could be reached.")
        
    try:
        response_text = await asyncio.to_thread(call_gemini)
        
        # Clean up the response if it accidentally has markdown blocks
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        clean_text = clean_text.strip()
        
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error from Gemini: {e}")
        print(f"Raw response: {response_text}")
        return {
            "hype_level": "Medium",
            "story": "Failed to parse AI summary.",
            "recent_buzz": [],
            "sentiment": "Unknown",
            "risk_signals": ["AI Parsing Error"],
            "tags": []
        }
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return {
            "hype_level": "Medium",
            "story": f"AI summarization failed: {e}",
            "recent_buzz": [],
            "sentiment": "Unknown",
            "risk_signals": ["API Error"],
            "tags": []
        }
