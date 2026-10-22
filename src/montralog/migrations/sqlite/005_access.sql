CREATE TABLE IF NOT EXISTS access_collections (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('team','group')),
 name TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, UNIQUE(kind,name)
);
CREATE TABLE IF NOT EXISTS access_members (
 collection_id TEXT NOT NULL REFERENCES access_collections(id),
 user_id TEXT NOT NULL REFERENCES users(id), PRIMARY KEY(collection_id,user_id)
);
CREATE TABLE IF NOT EXISTS access_audit (
 id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, action TEXT NOT NULL,
 target TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS identity_providers (provider TEXT PRIMARY KEY, config TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS external_identities (
 provider TEXT NOT NULL, issuer TEXT NOT NULL, subject TEXT NOT NULL,
 user_id TEXT NOT NULL REFERENCES users(id), PRIMARY KEY(provider,issuer,subject)
);
CREATE TABLE IF NOT EXISTS identity_states (
 state_hash TEXT PRIMARY KEY, provider TEXT NOT NULL, binding_hash TEXT NOT NULL,
 nonce TEXT NOT NULL, verifier TEXT NOT NULL, source TEXT NOT NULL, expires_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS identity_state_source ON identity_states(source,expires_at);
