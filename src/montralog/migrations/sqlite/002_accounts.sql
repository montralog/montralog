CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 email TEXT NOT NULL, password_hash TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
 csrf TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, expires_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS login_attempts (
 id TEXT PRIMARY KEY, attempt_key TEXT NOT NULL, attempted_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS attempts_key ON login_attempts(attempt_key,attempted_at);
CREATE TABLE IF NOT EXISTS dashboards (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), name TEXT NOT NULL,
 definition TEXT NOT NULL, updated_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS dashboards_user ON dashboards(user_id);
