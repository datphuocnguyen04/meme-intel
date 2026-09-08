import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "app.db")


def get_db_connection() -> sqlite3.Connection:
    """
    Create and return an optimized SQLite database connection.
    Leverages 64GB RAM with WAL mode, memory-mapped I/O, and in-memory page caching.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Extreme speed PRAGMAs
    conn.execute("PRAGMA journal_mode = WAL;")        # Concurrent read/write without locks
    conn.execute("PRAGMA synchronous = NORMAL;")       # Fast disk sync safely in WAL mode
    conn.execute("PRAGMA cache_size = -64000;")        # 64MB dedicated RAM page cache
    conn.execute("PRAGMA mmap_size = 268435456;")      # 256MB memory-mapped I/O directly in RAM
    conn.execute("PRAGMA temp_store = MEMORY;")        # Store temporary tables & sorts in RAM
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initialize database tables for tokens, tweets, and narratives."""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Tokens Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_address TEXT NOT NULL UNIQUE,
                symbol TEXT,
                name TEXT,
                chain TEXT,
                image_url TEXT,
                pair_address TEXT,
                is_watchlist INTEGER DEFAULT 0,
                total_supply REAL DEFAULT 0,
                total_holders INTEGER DEFAULT 0,
                total_supply_held REAL DEFAULT 0,
                total_supply_held_pct REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                last_fetched_at TEXT DEFAULT (datetime('now'))
            );
        """)

        # Migration: Ensure new columns exist on existing databases
        cursor.execute("PRAGMA table_info(tokens);")
        token_cols = [row[1] for row in cursor.fetchall()]
        if "total_supply" not in token_cols:
            cursor.execute("ALTER TABLE tokens ADD COLUMN total_supply REAL DEFAULT 0;")
        if "total_holders" not in token_cols:
            cursor.execute("ALTER TABLE tokens ADD COLUMN total_holders INTEGER DEFAULT 0;")
        if "total_supply_held" not in token_cols:
            cursor.execute("ALTER TABLE tokens ADD COLUMN total_supply_held REAL DEFAULT 0;")
        if "total_supply_held_pct" not in token_cols:
            cursor.execute("ALTER TABLE tokens ADD COLUMN total_supply_held_pct REAL DEFAULT 0;")
        if "quote_symbol" not in token_cols:
            cursor.execute("ALTER TABLE tokens ADD COLUMN quote_symbol TEXT DEFAULT '';")
        if "pair_label" not in token_cols:
            cursor.execute("ALTER TABLE tokens ADD COLUMN pair_label TEXT DEFAULT '';")

        # 2. Tweets Table (relational, deduplicated by tweet_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tweets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                tweet_id TEXT NOT NULL UNIQUE,
                username TEXT,
                display_name TEXT,
                followers INTEGER DEFAULT 0,
                verified INTEGER DEFAULT 0,
                text TEXT,
                tweet_url TEXT,
                profile_image TEXT,
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0,
                posted_at TEXT,
                fetched_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (token_id) REFERENCES tokens(id) ON DELETE CASCADE
            );
        """)

        # 3. Narratives Table (versioned analysis history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS narratives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                story TEXT,
                sentiment TEXT,
                hype_level TEXT,
                recent_buzz TEXT, -- JSON array of buzz lines
                low_confidence INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (token_id) REFERENCES tokens(id) ON DELETE CASCADE
            );
        """)

        # 4. Top Holders Table (from blockchain RPC)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS top_holders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                balance TEXT,
                percentage REAL,
                value_usd REAL,
                rank INTEGER,
                source TEXT DEFAULT 'rpc',
                fetched_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (token_id) REFERENCES tokens(id) ON DELETE CASCADE
            );
        """)

        # 5. Top PnL Traders Table (from on-chain Swap events)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS top_traders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                wallet_address TEXT NOT NULL,
                total_volume_usd REAL DEFAULT 0,
                buy_count INTEGER DEFAULT 0,
                sell_count INTEGER DEFAULT 0,
                total_bought_usd REAL DEFAULT 0,
                total_sold_usd REAL DEFAULT 0,
                estimated_pnl_usd REAL DEFAULT 0,
                estimated_pnl_pct REAL DEFAULT 0,
                rank INTEGER,
                fetched_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (token_id) REFERENCES tokens(id) ON DELETE CASCADE
            );
        """)

        # High-performance B-Tree Indexes for sub-millisecond lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_contract ON tokens(contract_address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tweets_token_id ON tweets(token_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_narratives_token_id ON narratives(token_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_holders_token_id ON top_holders(token_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_traders_token_id ON top_traders(token_id);")

        conn.commit()
