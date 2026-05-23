-- Finance Bot — schema completo
-- Cole este arquivo inteiro no SQL Editor do Supabase e execute.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS settings (
    id           SERIAL PRIMARY KEY,
    key          TEXT UNIQUE NOT NULL,
    value        TEXT NOT NULL,
    updated_at   TIMESTAMPTZ DEFAULT now()
);

INSERT INTO settings (key, value) VALUES
    ('base_balance', '0'),
    ('scheduler_timezone', 'America/Sao_Paulo')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS cards (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    type         TEXT NOT NULL CHECK (type IN ('credit','debit')),
    card_limit   NUMERIC(12,2),
    closing_day  INT,
    due_day      INT,
    active       BOOLEAN DEFAULT true,
    owner        TEXT,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transactions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date         DATE NOT NULL,
    type         TEXT NOT NULL CHECK (type IN ('income','expense')),
    category     TEXT NOT NULL,
    description  TEXT NOT NULL,
    amount       NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    card_id      UUID REFERENCES cards(id) ON DELETE SET NULL,
    "user"       TEXT,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);

CREATE TABLE IF NOT EXISTS subscriptions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    amount       NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    frequency    TEXT NOT NULL CHECK (frequency IN ('monthly','annual')),
    next_date    DATE NOT NULL,
    active       BOOLEAN DEFAULT true,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS goals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    target_amount   NUMERIC(12,2) NOT NULL CHECK (target_amount > 0),
    current_amount  NUMERIC(12,2) NOT NULL DEFAULT 0,
    deadline        DATE,
    completed       BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS seasonal_reserves (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    amount       NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    month        INT NOT NULL CHECK (month BETWEEN 1 AND 12),
    created_at   TIMESTAMPTZ DEFAULT now()
);
