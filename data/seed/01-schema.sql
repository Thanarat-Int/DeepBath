-- ─────────────────────────────────────────────────────────────────────────────
--  AutoX-SCB AI · Postgres seed schema
--  Auto-applied by the Postgres container via /docker-entrypoint-initdb.d
-- ─────────────────────────────────────────────────────────────────────────────

-- pgvector for RAG
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Customer / accounts (synthetic, no real PII) ─────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    customer_id   TEXT PRIMARY KEY,
    full_name     TEXT NOT NULL,
    monthly_income NUMERIC(12, 2),
    risk_profile  TEXT CHECK (risk_profile IN ('conservative', 'moderate', 'aggressive'))
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id    TEXT PRIMARY KEY,
    customer_id   TEXT REFERENCES customers(customer_id),
    account_type  TEXT CHECK (account_type IN ('savings', 'checking', 'credit')),
    balance       NUMERIC(14, 2) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id        BIGSERIAL PRIMARY KEY,
    account_id    TEXT REFERENCES accounts(account_id),
    txn_date      DATE NOT NULL,
    amount        NUMERIC(12, 2) NOT NULL,    -- negative = debit, positive = credit
    category      TEXT,                        -- 'food', 'transport', 'shopping', 'salary', ...
    merchant      TEXT,
    description   TEXT
);

CREATE INDEX IF NOT EXISTS idx_txn_account_date ON transactions(account_id, txn_date DESC);
CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category);

-- ── Policy docs (RAG store) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS policy_chunks (
    chunk_id      BIGSERIAL PRIMARY KEY,
    doc_id        TEXT NOT NULL,
    doc_title     TEXT NOT NULL,
    chunk_index   INTEGER NOT NULL,
    content       TEXT NOT NULL,
    embedding     vector(1024),               -- bge-m3 dimension
    metadata      JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_policy_doc ON policy_chunks(doc_id);
-- Vector index added in Day-1 afternoon after embeddings are populated:
--   CREATE INDEX ON policy_chunks USING hnsw (embedding vector_cosine_ops);
