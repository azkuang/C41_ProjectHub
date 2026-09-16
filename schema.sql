CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    source_type   TEXT NOT NULL CHECK (source_type IN ('upload', 'drive')),
    filename      TEXT,
    drive_url     TEXT,
    uploader_name TEXT NOT NULL,
    upload_date   TEXT NOT NULL DEFAULT (datetime('now'))
);
