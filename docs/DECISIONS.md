# 📜 Architectural Decision Records (ADRs)

---

## ADR-001: Direct Blockchain RPC vs Third-Party APIs for Wallets
- **Status**: Accepted
- **Context**: Third-party aggregators (GeckoTerminal, Birdeye, Moralis) either have restrictive rate limits, require paid API keys, or have incomplete support for emerging L2s like Robinhood Chain or Ink Chain.
- **Decision**: Query EVM nodes directly using standard JSON-RPC (`eth_call` for `totalSupply()`, `eth_getLogs` for `Transfer` and `Swap` logs).
- **Consequences**: Zero recurring API costs, instant support for any EVM-compatible chain, and complete resistance to aggregator downtime.

---

## ADR-002: SQLite with WAL Mode and Non-Destructive Migrations
- **Status**: Accepted
- **Context**: Need lightweight persistent storage for narratives, tweets, and holders that requires zero daemon setup (Postgres/Redis) while providing `< 1ms` query speeds.
- **Decision**: Use SQLite in WAL (Write-Ahead Logging) mode with `mmap_size = 268435456` and synchronous = NORMAL. Schema modifications must be performed via `PRAGMA table_info` checks with `ALTER TABLE ADD COLUMN` to guarantee non-destructive migrations.
- **Consequences**: Blazing fast disk queries, zero configuration, portable `.db` file, and no data loss on restarts.

---

## ADR-003: Modular Vanilla Frontend Architecture
- **Status**: Accepted
- **Context**: A 3,000+ line monolithic `index.html` was difficult to maintain and caused high context window usage for AI coding agents.
- **Decision**: Split the frontend into three clean files: `frontend/index.html` (markup), `frontend/css/styles.css` (design), and `frontend/js/app.js` (logic).
- **Consequences**: Clean separation of concerns, fast browser rendering without bundler bloat, and easy token-efficient targeted edits by AI agents.
