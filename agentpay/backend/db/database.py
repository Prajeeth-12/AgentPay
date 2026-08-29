import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agentpay.db")


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    public_key_jwk  TEXT NOT NULL,
    status          TEXT DEFAULT 'active',
    max_budget      INTEGER NOT NULL,
    registered_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    user_intent     TEXT,
    parsed_intent   TEXT,
    budget_limit    INTEGER NOT NULL,
    budget_spent    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'active',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mandates (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    type            TEXT NOT NULL,
    vct             TEXT NOT NULL,
    payload         TEXT NOT NULL,
    sd_jwt          TEXT,
    mandate_hash    TEXT,
    constraints     TEXT,
    status          TEXT DEFAULT 'created',
    parent_id       TEXT REFERENCES mandates(id),
    signed_by       TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    product_id      TEXT NOT NULL,
    product_title   TEXT NOT NULL,
    price           INTEGER NOT NULL,
    quantity        INTEGER DEFAULT 1,
    added_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    mandate_id      TEXT NOT NULL REFERENCES mandates(id),
    razorpay_order_id   TEXT,
    razorpay_payment_id TEXT,
    razorpay_link_id    TEXT,
    razorpay_link_url   TEXT,
    amount          INTEGER NOT NULL,
    currency        TEXT DEFAULT 'INR',
    status          TEXT DEFAULT 'created',
    razorpay_signature  TEXT,
    webhook_payload     TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    timestamp       TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    agent_id        TEXT,
    mandate_id      TEXT REFERENCES mandates(id),
    mandate_type    TEXT,
    details         TEXT NOT NULL,
    razorpay_refs   TEXT,
    constraint_check TEXT
);
"""
