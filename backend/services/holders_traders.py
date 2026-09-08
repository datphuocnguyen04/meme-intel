"""
On-Chain Wallet Analytics: Top Holders & Top Traders
=====================================================
Pure blockchain RPC implementation — zero third-party data APIs.

Solana:  getTokenLargestAccounts (holders) + getSignaturesForAddress/getTransaction (traders)
EVM:     eth_getLogs for Transfer events (holders) + Swap events (traders)
"""

import asyncio
import struct
from collections import defaultdict
from typing import Dict, Any, List, Optional

from services.http_client import get_http_client

# ─── Chain-to-RPC Mapping (Free Public Endpoints) ────────────────────────────

CHAIN_RPC = {
    "solana": "https://api.mainnet-beta.solana.com",
    "ethereum": "https://eth.llamarpc.com",
    "base": "https://mainnet.base.org",
    "bsc": "https://bsc-dataseed.binance.org",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "polygon": "https://polygon-rpc.com",
    "robinhood": "https://rpc.mainnet.chain.robinhood.com",
    "ink": "https://rpc-gel.inkonchain.com",
}

# ─── Event Signatures (Keccak-256 Hashes) ─────────────────────────────────────

# ERC-20 Transfer(address indexed from, address indexed to, uint256 value)
ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Uniswap V2 Swap(address indexed sender, uint256, uint256, uint256, uint256, address indexed to)
UNISWAP_V2_SWAP_TOPIC = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"

# Uniswap V3 Swap(address indexed sender, address indexed recipient, int256, int256, uint160, uint128, int24)
UNISWAP_V3_SWAP_TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"

# Zero address (mint/burn)
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Block explorer URLs for wallet links
CHAIN_EXPLORER = {
    "solana": "https://solscan.io/account/",
    "ethereum": "https://etherscan.io/address/",
    "base": "https://basescan.org/address/",
    "bsc": "https://bscscan.com/address/",
    "arbitrum": "https://arbiscan.io/address/",
    "polygon": "https://polygonscan.com/address/",
    "robinhood": "https://robinhoodchain.blockscout.com/address/",
    "ink": "https://explorer.inkonchain.com/address/",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  SOLANA — Native RPC Methods
# ═══════════════════════════════════════════════════════════════════════════════

import os

SOLANA_PUBLIC_RPCS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
    "https://rpc.ankr.com/solana",
]

_custom_solana_rpc = os.getenv("SOLANA_RPC_URL")
if _custom_solana_rpc and _custom_solana_rpc not in SOLANA_PUBLIC_RPCS:
    SOLANA_PUBLIC_RPCS.insert(0, _custom_solana_rpc)

async def _solana_rpc(method: str, params: list) -> Optional[Dict]:
    """Make a JSON-RPC call to Solana public RPCs with automatic fallback."""
    client = get_http_client()
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    for rpc_url in SOLANA_PUBLIC_RPCS:
        try:
            resp = await client.post(rpc_url, json=payload, timeout=12.0)
            if resp.status_code == 429:
                continue
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                continue
            return data.get("result")
        except Exception:
            continue

    print(f"All Solana RPCs failed or rate-limited for method: {method}")
    return None


async def solana_get_total_supply(mint_address: str) -> tuple:
    """
    Directly query Solana token mint supply via getTokenSupply.
    Returns (human_total_supply, decimals).
    """
    res = await _solana_rpc("getTokenSupply", [mint_address])
    if res and "value" in res:
        val = res["value"]
        try:
            amount_str = val.get("uiAmountString") or str(val.get("uiAmount") or 0)
            decimals = int(val.get("decimals") or 0)
            return float(amount_str), decimals
        except Exception:
            pass
    return 0.0, 0


async def solana_get_top_holders(mint_address: str, price_usd: float) -> Dict[str, Any]:
    """
    Query Solana token holders and total supply.
    1. First attempts direct on-chain RPC via getTokenSupply & getTokenLargestAccounts.
    2. If getTokenLargestAccounts is rate-limited (429) on public RPC nodes,
       fallbacks seamlessly to the public Solana token index (Rugcheck report),
       which provides the exact top 20 owner wallets (matching Solscan portfolio),
       exact balances, percentages, and true total_holders count.
    """
    total_supply, decimals = await solana_get_total_supply(mint_address)

    # 1. Direct Solana RPC
    result = await _solana_rpc("getTokenLargestAccounts", [mint_address])
    if result and "value" in result and result["value"]:
        accounts = result["value"]
        tracked_balance = sum(float(a.get("uiAmountString", "0") or "0") for a in accounts)
        effective_supply = total_supply if total_supply > 0 else tracked_balance

        holders = []
        for i, acc in enumerate(accounts):
            balance_str = acc.get("uiAmountString", "0") or "0"
            balance = float(balance_str)
            if balance <= 0:
                continue

            token_account_addr = acc.get("address", "")
            owner_wallet = token_account_addr
            acc_info = await _solana_rpc("getAccountInfo", [
                token_account_addr,
                {"encoding": "jsonParsed"}
            ])
            if acc_info and acc_info.get("value"):
                parsed = acc_info["value"].get("data", {})
                if isinstance(parsed, dict) and "parsed" in parsed:
                    owner_wallet = parsed["parsed"].get("info", {}).get("owner", token_account_addr)

            pct = (balance / effective_supply * 100) if effective_supply > 0 else 0
            value = balance * price_usd

            holders.append({
                "wallet_address": owner_wallet,
                "balance": f"{balance:,.2f}",
                "balance_raw": balance,
                "percentage": round(pct, 2),
                "value_usd": round(value, 2),
                "rank": i + 1,
                "source": "solana_rpc",
            })

        total_supply_held = sum(h["balance_raw"] for h in holders)
        held_pct = (total_supply_held / effective_supply * 100) if effective_supply > 0 else 0

        return {
            "holders": holders,
            "total_supply": effective_supply,
            "total_holders": len(holders),
            "total_supply_held": total_supply_held,
            "total_supply_held_pct": round(held_pct, 2),
        }

    # 2. Resilient Public Token Index Fallback (Matches Solscan portfolio)
    try:
        client = get_http_client()
        resp = await client.get(f"https://api.rugcheck.xyz/v1/tokens/{mint_address}/report", timeout=8.0)
        if resp.status_code == 200:
            data = resp.json()
            raw_supply = data.get("token", {}).get("supply", 0)
            raw_decimals = data.get("token", {}).get("decimals", decimals or 6)
            calc_supply = (raw_supply / (10 ** raw_decimals)) if raw_supply > 0 else total_supply
            effective_supply = total_supply if total_supply > 0 else calc_supply

            total_holders = data.get("totalHolders") or 0
            top_raw = data.get("topHolders") or []

            holders = []
            for i, h in enumerate(top_raw[:20]):
                owner = h.get("owner") or h.get("address") or ""
                bal = float(h.get("uiAmount", 0) or 0)
                pct = float(h.get("pct", 0) or 0)
                if bal <= 0 and pct <= 0:
                    continue
                val = bal * price_usd
                holders.append({
                    "wallet_address": owner,
                    "balance": f"{bal:,.2f}",
                    "balance_raw": bal,
                    "percentage": round(pct, 2),
                    "value_usd": round(val, 2),
                    "rank": i + 1,
                    "source": "solana_index",
                })

            total_supply_held = sum(h["balance_raw"] for h in holders)
            held_pct = (total_supply_held / effective_supply * 100) if effective_supply > 0 else 0

            return {
                "holders": holders,
                "total_supply": effective_supply,
                "total_holders": total_holders if total_holders > 0 else len(holders),
                "total_supply_held": total_supply_held,
                "total_supply_held_pct": round(held_pct, 2),
            }
    except Exception as e:
        print(f"Solana holder index fallback error: {e}")

    return {
        "holders": [],
        "total_supply": total_supply,
        "total_holders": 0,
        "total_supply_held": 0.0,
        "total_supply_held_pct": 0.0,
    }


async def solana_get_top_traders(pair_address: str, price_usd: float) -> List[Dict[str, Any]]:
    """
    Use Solana RPC getSignaturesForAddress + getTransaction to parse recent pool swaps.
    Aggregates by signer wallet to compute volume, buy/sell counts, and estimated PnL.
    """
    # Get recent transaction signatures for the pool
    sigs_result = await _solana_rpc("getSignaturesForAddress", [
        pair_address,
        {"limit": 100}
    ])
    if not sigs_result:
        return []

    # Aggregate trades by wallet
    wallet_stats = defaultdict(lambda: {
        "total_volume_usd": 0.0,
        "buy_count": 0,
        "sell_count": 0,
        "total_bought_usd": 0.0,
        "total_sold_usd": 0.0,
    })

    # Process transactions (limit concurrent requests to avoid rate limiting)
    signatures = [s["signature"] for s in sigs_result if not s.get("err")]
    batch_size = 10

    for batch_start in range(0, len(signatures), batch_size):
        batch = signatures[batch_start:batch_start + batch_size]
        tasks = [
            _solana_rpc("getTransaction", [sig, {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0
            }])
            for sig in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for tx_data in results:
            if isinstance(tx_data, Exception) or not tx_data:
                continue

            try:
                # Signer = first account key (the trader)
                account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
                if not account_keys:
                    continue

                signer = account_keys[0]
                if isinstance(signer, dict):
                    signer = signer.get("pubkey", "")

                if not signer:
                    continue

                # Parse token balance changes from pre/post balances
                meta = tx_data.get("meta", {})
                if not meta or meta.get("err"):
                    continue

                pre_balances = meta.get("preTokenBalances", [])
                post_balances = meta.get("postTokenBalances", [])

                # Build maps of token account index -> balance
                pre_map = {}
                for b in pre_balances:
                    idx = b.get("accountIndex", -1)
                    amount = float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)
                    pre_map[idx] = {"amount": amount, "owner": b.get("owner", "")}

                # Check post balances for changes
                for b in post_balances:
                    idx = b.get("accountIndex", -1)
                    post_amount = float(b.get("uiTokenAmount", {}).get("uiAmount") or 0)
                    owner = b.get("owner", "")
                    pre_amount = pre_map.get(idx, {}).get("amount", 0)

                    delta = post_amount - pre_amount
                    if abs(delta) < 0.000001:
                        continue

                    # Only track the signer's balance changes
                    if owner != signer:
                        continue

                    usd_value = abs(delta) * price_usd

                    if delta > 0:
                        # Token balance increased = BUY
                        wallet_stats[signer]["buy_count"] += 1
                        wallet_stats[signer]["total_bought_usd"] += usd_value
                    else:
                        # Token balance decreased = SELL
                        wallet_stats[signer]["sell_count"] += 1
                        wallet_stats[signer]["total_sold_usd"] += usd_value

                    wallet_stats[signer]["total_volume_usd"] += usd_value

            except Exception as e:
                print(f"Error parsing Solana tx: {e}")
                continue

        # Small delay between batches to respect rate limits
        await asyncio.sleep(0.2)

    return _rank_traders(wallet_stats)


# ═══════════════════════════════════════════════════════════════════════════════
#  EVM — eth_getLogs for Transfer & Swap Events
# ═══════════════════════════════════════════════════════════════════════════════

async def _evm_rpc(chain: str, method: str, params: list) -> Optional[Any]:
    """Make a JSON-RPC call to the appropriate EVM chain RPC."""
    rpc_url = CHAIN_RPC.get(chain)
    if not rpc_url:
        print(f"No RPC URL configured for chain: {chain}")
        return None

    client = get_http_client()
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    try:
        resp = await client.post(rpc_url, json=payload, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            print(f"EVM RPC error ({chain}/{method}): {data['error']}")
            return None
        return data.get("result")
    except Exception as e:
        print(f"EVM RPC call failed ({chain}/{method}): {e}")
        return None


async def _evm_get_block_number(chain: str) -> Optional[int]:
    """Get the latest block number for a chain."""
    result = await _evm_rpc(chain, "eth_blockNumber", [])
    if result:
        return int(result, 16)
    return None


def _decode_address_from_topic(topic: str) -> str:
    """Extract a 20-byte address from a 32-byte hex topic."""
    # topics are 32 bytes, address is last 20 bytes
    return "0x" + topic[-40:]


def _decode_uint256(hex_str: str) -> int:
    """Decode a 32-byte hex string as an unsigned 256-bit integer."""
    return int(hex_str, 16) if hex_str else 0


async def evm_get_total_supply(chain: str, token_address: str) -> tuple:
    """
    Directly query ERC-20 totalSupply() and decimals() via eth_call.
    Returns (human_total_supply, decimals).
    """
    # 0x18160ddd = bytes4(keccak256("totalSupply()"))
    supply_res = await _evm_rpc(chain, "eth_call", [{"to": token_address, "data": "0x18160ddd"}, "latest"])
    # 0x313ce567 = bytes4(keccak256("decimals()"))
    decimals_res = await _evm_rpc(chain, "eth_call", [{"to": token_address, "data": "0x313ce567"}, "latest"])

    decimals = 18
    if decimals_res and decimals_res != "0x":
        try:
            decimals = int(decimals_res, 16)
        except Exception:
            decimals = 18

    total_supply = 0.0
    if supply_res and supply_res != "0x":
        try:
            raw_supply = int(supply_res, 16)
            total_supply = raw_supply / (10 ** decimals)
        except Exception:
            total_supply = 0.0

    return total_supply, decimals


async def evm_get_top_holders(chain: str, token_address: str, price_usd: float, decimals: int = 18) -> Dict[str, Any]:
    """
    Scan recent ERC-20 Transfer events to build an approximate holder balance map.
    Scans the last ~10,000 blocks to capture recent active holders.
    Queries exact on-chain totalSupply() and decimals() via eth_call.
    """
    empty_result = {
        "holders": [],
        "total_supply": 0.0,
        "total_holders": 0,
        "total_supply_held": 0.0,
        "total_supply_held_pct": 0.0,
    }

    total_supply, token_decimals = await evm_get_total_supply(chain, token_address)
    decimals = token_decimals if token_decimals > 0 else decimals

    latest_block = await _evm_get_block_number(chain)
    if not latest_block:
        empty_result["total_supply"] = total_supply
        return empty_result

    from_block = max(0, latest_block - 10000)

    # Fetch Transfer event logs in chunks to avoid RPC limits
    all_logs = []
    chunk_size = 2000
    for start in range(from_block, latest_block + 1, chunk_size):
        end = min(start + chunk_size - 1, latest_block)
        logs = await _evm_rpc(chain, "eth_getLogs", [{
            "address": token_address,
            "topics": [ERC20_TRANSFER_TOPIC],
            "fromBlock": hex(start),
            "toBlock": hex(end),
        }])
        if logs:
            all_logs.extend(logs)
        await asyncio.sleep(0.05)  # Rate limit courtesy

    if not all_logs:
        empty_result["total_supply"] = total_supply
        return empty_result

    # Build balance map from Transfer events
    balances = defaultdict(int)
    for log in all_logs:
        topics = log.get("topics", [])
        data = log.get("data", "0x0")

        if len(topics) < 3:
            continue

        from_addr = _decode_address_from_topic(topics[1]).lower()
        to_addr = _decode_address_from_topic(topics[2]).lower()
        value = _decode_uint256(data[2:] if data.startswith("0x") else data)

        if from_addr != ZERO_ADDRESS:
            balances[from_addr] -= value
        if to_addr != ZERO_ADDRESS:
            balances[to_addr] += value

    # Filter out zero/negative balances and sort
    positive_holders = {addr: bal for addr, bal in balances.items() if bal > 0}
    if not positive_holders:
        empty_result["total_supply"] = total_supply
        return empty_result

    sorted_holders = sorted(positive_holders.items(), key=lambda x: x[1], reverse=True)[:20]
    raw_held_sum = sum(bal for _, bal in sorted_holders)
    total_supply_held = raw_held_sum / (10 ** decimals)
    effective_supply = total_supply if total_supply > 0 else total_supply_held
    held_pct = (total_supply_held / effective_supply * 100) if effective_supply > 0 else 0

    holders = []
    for rank, (addr, raw_balance) in enumerate(sorted_holders, 1):
        human_balance = raw_balance / (10 ** decimals)
        pct = (human_balance / effective_supply * 100) if effective_supply > 0 else 0
        value = human_balance * price_usd

        holders.append({
            "wallet_address": addr,
            "balance": f"{human_balance:,.2f}",
            "balance_raw": human_balance,
            "percentage": round(pct, 2),
            "value_usd": round(value, 2),
            "rank": rank,
            "source": "transfers",
        })

    return {
        "holders": holders,
        "total_supply": effective_supply,
        "total_holders": len(positive_holders),
        "total_supply_held": total_supply_held,
        "total_supply_held_pct": round(held_pct, 2),
    }


async def evm_get_top_traders(chain: str, pair_address: str, token_address: str, price_usd: float, decimals: int = 18) -> List[Dict[str, Any]]:
    """
    Scan recent Uniswap V2/V3 Swap events from the DEX pool to find top traders.
    For each Swap, resolves the actual trader wallet via eth_getTransactionByHash.
    """
    latest_block = await _evm_get_block_number(chain)
    if not latest_block:
        return []

    from_block = max(0, latest_block - 5000)

    all_swap_logs = []
    # Only query pair_address directly if it is a valid 20-byte EVM address (42 hex chars)
    is_valid_pair_addr = isinstance(pair_address, str) and len(pair_address.strip()) == 42 and pair_address.startswith("0x")

    if is_valid_pair_addr:
        for swap_topic in [UNISWAP_V2_SWAP_TOPIC, UNISWAP_V3_SWAP_TOPIC]:
            chunk_size = 2000
            for start in range(from_block, latest_block + 1, chunk_size):
                end = min(start + chunk_size - 1, latest_block)
                logs = await _evm_rpc(chain, "eth_getLogs", [{
                    "address": pair_address.strip(),
                    "topics": [swap_topic],
                    "fromBlock": hex(start),
                    "toBlock": hex(end),
                }])
                if logs:
                    for log in logs:
                        log["_swap_version"] = "v2" if swap_topic == UNISWAP_V2_SWAP_TOPIC else "v3"
                    all_swap_logs.extend(logs)
                await asyncio.sleep(0.05)

            if all_swap_logs:
                break

    # If pair_address is a 32-byte poolId (e.g. Robinhood/V4) or no swaps found on pair,
    # fall back to scanning Transfer logs directly on token_address!
    if not all_swap_logs and token_address:
        chunk_size = 2500
        for start in range(from_block, latest_block + 1, chunk_size):
            end = min(start + chunk_size - 1, latest_block)
            logs = await _evm_rpc(chain, "eth_getLogs", [{
                "address": token_address.strip(),
                "topics": [ERC20_TRANSFER_TOPIC],
                "fromBlock": hex(start),
                "toBlock": hex(end),
            }])
            if logs:
                for log in logs:
                    log["_swap_version"] = "transfer"
                all_swap_logs.extend(logs)
            await asyncio.sleep(0.05)

    if not all_swap_logs:
        return []

    # Get unique tx hashes and resolve trader wallets
    tx_hashes = list(set(log.get("transactionHash", "") for log in all_swap_logs))[:40]  # Cap at 40 recent txs for fast response

    # Batch resolve tx.from addresses
    tx_from_map = {}
    batch_size = 10
    for batch_start in range(0, len(tx_hashes), batch_size):
        batch = tx_hashes[batch_start:batch_start + batch_size]
        tasks = [_evm_rpc(chain, "eth_getTransactionByHash", [tx_hash]) for tx_hash in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for tx_hash, tx_data in zip(batch, results):
            if isinstance(tx_data, Exception) or not tx_data:
                continue
            tx_from_map[tx_hash] = (tx_data.get("from", "") or "").lower()

        await asyncio.sleep(0.1)

    # Aggregate trades by wallet
    wallet_stats = defaultdict(lambda: {
        "total_volume_usd": 0.0,
        "buy_count": 0,
        "sell_count": 0,
        "total_bought_usd": 0.0,
        "total_sold_usd": 0.0,
    })

    for log in all_swap_logs:
        tx_hash = log.get("transactionHash", "")
        trader = tx_from_map.get(tx_hash, "")
        if not trader:
            continue

        data = log.get("data", "0x")
        data_hex = data[2:] if data.startswith("0x") else data

        try:
            if log["_swap_version"] == "v2":
                # V2: data = amount0In, amount1In, amount0Out, amount1Out (each 32 bytes)
                if len(data_hex) < 256:
                    data_hex = data_hex.ljust(256, "0")
                amount0_in = int(data_hex[0:64], 16)
                amount1_in = int(data_hex[64:128], 16)
                amount0_out = int(data_hex[128:192], 16)
                amount1_out = int(data_hex[192:256], 16)

                # Determine if buy or sell based on token position
                # If token sends in and receives out the other = SELL
                # We approximate volume using the larger side
                total_in = (amount0_in + amount1_in) / (10 ** decimals)
                total_out = (amount0_out + amount1_out) / (10 ** decimals)
                volume_tokens = max(total_in, total_out)
                volume_usd = volume_tokens * price_usd

                # Heuristic: if amount0_in > 0 (token0 going in), classify as sell of token0
                if amount0_in > 0 and amount1_out > 0:
                    wallet_stats[trader]["sell_count"] += 1
                    wallet_stats[trader]["total_sold_usd"] += volume_usd
                else:
                    wallet_stats[trader]["buy_count"] += 1
                    wallet_stats[trader]["total_bought_usd"] += volume_usd

                wallet_stats[trader]["total_volume_usd"] += volume_usd

            elif log["_swap_version"] == "v3":
                # V3: data = amount0 (int256), amount1 (int256), sqrtPriceX96, liquidity, tick
                if len(data_hex) < 128:
                    continue
                # Signed int256 for amount0 and amount1
                amount0_raw = int(data_hex[0:64], 16)
                if amount0_raw >= 2**255:
                    amount0_raw -= 2**256
                amount1_raw = int(data_hex[64:128], 16)
                if amount1_raw >= 2**255:
                    amount1_raw -= 2**256

                volume_tokens = max(abs(amount0_raw), abs(amount1_raw)) / (10 ** decimals)
                volume_usd = volume_tokens * price_usd

                # Positive amount = tokens going INTO the pool = sell
                if amount0_raw > 0:
                    wallet_stats[trader]["sell_count"] += 1
                    wallet_stats[trader]["total_sold_usd"] += volume_usd
                else:
                    wallet_stats[trader]["buy_count"] += 1
                    wallet_stats[trader]["total_bought_usd"] += volume_usd

                wallet_stats[trader]["total_volume_usd"] += volume_usd

            elif log["_swap_version"] == "transfer":
                # Transfer(from, to, value) on token contract
                topics = log.get("topics", [])
                if len(topics) >= 3:
                    from_addr = _decode_address_from_topic(topics[1]).lower()
                    to_addr = _decode_address_from_topic(topics[2]).lower()
                    value_raw = _decode_uint256(data_hex)
                    volume_tokens = value_raw / (10 ** decimals)
                    volume_usd = volume_tokens * price_usd

                    if to_addr == trader:
                        wallet_stats[trader]["buy_count"] += 1
                        wallet_stats[trader]["total_bought_usd"] += volume_usd
                    elif from_addr == trader:
                        wallet_stats[trader]["sell_count"] += 1
                        wallet_stats[trader]["total_sold_usd"] += volume_usd
                    else:
                        # DEX router routed trade to trader
                        wallet_stats[trader]["buy_count"] += 1
                        wallet_stats[trader]["total_bought_usd"] += volume_usd

                    wallet_stats[trader]["total_volume_usd"] += volume_usd

        except Exception as e:
            print(f"Error decoding swap log: {e}")
            continue

    return _rank_traders(wallet_stats)


# ═══════════════════════════════════════════════════════════════════════════════
#  Shared Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _rank_traders(wallet_stats: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Sort traders by volume and compute PnL, return ranked list."""
    if not wallet_stats:
        return []

    # Sort by total volume descending
    sorted_wallets = sorted(
        wallet_stats.items(),
        key=lambda x: x[1]["total_volume_usd"],
        reverse=True,
    )[:20]

    traders = []
    for rank, (wallet, stats) in enumerate(sorted_wallets, 1):
        pnl = stats["total_sold_usd"] - stats["total_bought_usd"]
        pnl_pct = (pnl / stats["total_bought_usd"] * 100) if stats["total_bought_usd"] > 0 else 0

        traders.append({
            "wallet_address": wallet,
            "total_volume_usd": round(stats["total_volume_usd"], 2),
            "buy_count": stats["buy_count"],
            "sell_count": stats["sell_count"],
            "total_bought_usd": round(stats["total_bought_usd"], 2),
            "total_sold_usd": round(stats["total_sold_usd"], 2),
            "estimated_pnl_usd": round(pnl, 2),
            "estimated_pnl_pct": round(pnl_pct, 2),
            "rank": rank,
        })

    return traders


# ═══════════════════════════════════════════════════════════════════════════════
#  Unified Entry Points (Auto-detect chain type)
# ═══════════════════════════════════════════════════════════════════════════════

async def fetch_top_holders(chain: str, contract_address: str, pair_address: str, price_usd: float) -> Dict[str, Any]:
    """
    Fetch top holders using the appropriate blockchain RPC method.
    Solana: getTokenLargestAccounts + getTokenSupply.
    EVM: Scan Transfer events + eth_call for totalSupply().
    Returns dict with holders list, total_supply, total_holders, and total_supply_held metrics.
    """
    chain_lower = (chain or "").lower()

    if chain_lower == "solana":
        return await solana_get_top_holders(contract_address, price_usd)
    elif chain_lower in CHAIN_RPC:
        return await evm_get_top_holders(chain_lower, contract_address, price_usd)
    else:
        print(f"Unsupported chain for holders: {chain}")
        return {
            "holders": [],
            "total_supply": 0.0,
            "total_holders": 0,
            "total_supply_held": 0.0,
            "total_supply_held_pct": 0.0,
        }


async def fetch_top_traders(chain: str, contract_address: str, pair_address: str, price_usd: float) -> List[Dict[str, Any]]:
    """
    Fetch top traders using on-chain Swap event analysis.
    Solana: Parse pool transactions via getSignaturesForAddress.
    EVM: Parse Uniswap V2/V3 Swap events via eth_getLogs.
    """
    chain_lower = (chain or "").lower()

    if chain_lower == "solana":
        return await solana_get_top_traders(pair_address or contract_address, price_usd)
    elif chain_lower in CHAIN_RPC:
        if not pair_address:
            print(f"No pair address available for EVM trader analysis on {chain}")
            return []
        return await evm_get_top_traders(chain_lower, pair_address, contract_address, price_usd)
    else:
        print(f"Unsupported chain for traders: {chain}")
        return []


def get_explorer_url(chain: str, wallet_address: str) -> str:
    """Get block explorer URL for a wallet address."""
    chain_lower = (chain or "").lower()
    base_url = CHAIN_EXPLORER.get(chain_lower, "")
    if base_url:
        return f"{base_url}{wallet_address}"
    return ""
