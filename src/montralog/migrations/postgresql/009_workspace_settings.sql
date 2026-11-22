CREATE TABLE IF NOT EXISTS workspace_settings (
 id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL,
 description TEXT NOT NULL, updated_at DOUBLE PRECISION NOT NULL DEFAULT 0
);
INSERT INTO workspace_settings(id,name,description) VALUES (1,'Your organization','Your observability workspace') ON CONFLICT(id) DO NOTHING;
