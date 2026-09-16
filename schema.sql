CREATE TABLE IF NOT EXISTS projects (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                  TEXT NOT NULL UNIQUE,
    title                 TEXT NOT NULL,
    eyebrow               TEXT NOT NULL,
    production_label      TEXT,
    date_range_text       TEXT,
    date_year             TEXT,
    client_logo_filename  TEXT,
    coordinator_name      TEXT,
    coordinator_phone     TEXT,
    emergency_phone       TEXT NOT NULL DEFAULT '112',
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS credits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    name        TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_credits_project ON credits(project_id, sort_order, id);

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    section       TEXT NOT NULL CHECK (section IN ('document', 'callsheet', 'menu')),
    title         TEXT NOT NULL,
    subtitle      TEXT,
    source_type   TEXT NOT NULL CHECK (source_type IN ('upload', 'drive')),
    filename      TEXT,
    drive_url     TEXT,
    entry_date    TEXT,
    location      TEXT,
    uploader_name TEXT NOT NULL,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    upload_date   TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (section = 'document' OR entry_date IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_documents_project_section ON documents(project_id, section, sort_order, id);
