-- SQLite initial schema for CallAssist Pro
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(64),
    voice_preference VARCHAR(64),
    created_at DATETIME NOT NULL
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    tier VARCHAR(10) NOT NULL,
    status VARCHAR(9) NOT NULL,
    stripe_customer_id VARCHAR(64),
    stripe_subscription_id VARCHAR(64),
    renews_at DATETIME,
    updated_at DATETIME NOT NULL
);
CREATE TABLE IF NOT EXISTS call_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind VARCHAR(16) NOT NULL,
    number VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,
    note TEXT,
    created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_call_logs_user_id ON call_logs(user_id);
CREATE TABLE IF NOT EXISTS usage_records (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model VARCHAR(64) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost_usd FLOAT NOT NULL,
    created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_usage_records_user_id ON usage_records(user_id);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY,
    telegram_id BIGINT,
    action VARCHAR(64) NOT NULL,
    detail TEXT,
    created_at DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_telegram_id ON audit_logs(telegram_id);
