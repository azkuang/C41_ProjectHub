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

-- Seed the original "Zegna SS27" project (content from ProjectHub.html) so the
-- app ships with a real, populated example instead of an empty state. This
-- only ever runs once: schema.sql only executes when DATABASE_PATH doesn't
-- exist yet (see db.py:init_db()), so a running app's data is never touched.

INSERT INTO projects
    (slug, title, eyebrow, production_label, date_range_text, date_year,
     client_logo_filename, coordinator_name, coordinator_phone, emergency_phone)
VALUES
    ('zegna-ss27', 'Zegna SS27', 'ZEGNA SS27', 'PRODUCTION / SS27',
     '17 — 19 SEPTEMBER', '2026', 'zegna.png', 'Micol Lupi', '+393401458343', '112');

INSERT INTO credits (project_id, role, name, sort_order) VALUES
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'creative director', 'Alessandro Sartori', 0),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'photographer', 'Jeremy Everett', 1),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'director', 'Mattia Benetti', 2),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'dop', 'Edoardo Bolli', 3),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'still life', 'Mattia Parodi', 4),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'bts', 'Nicole Russo', 5);

INSERT INTO documents (project_id, section, title, subtitle, source_type, drive_url, uploader_name, sort_order) VALUES
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'ADV SHOTLIST', 'View PDF', 'drive', 'https://drive.google.com/file/d/1OpHnU2I50i3tnyC9_gDKzxwetsplb--A/view?usp=drivesdk', 'seed', 0),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'TREATMENT VIDEO', 'View PDF', 'drive', 'https://drive.google.com/file/d/1VEvkJyNqcXVoTT_rMEuwKN0rnwro37od/view?usp=drivesdk', 'seed', 1),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'ITALIAN LIVING MOMENTS', 'View PDF', 'drive', 'https://drive.google.com/file/d/11wg8xuSz-nLEwDVl3dSZp725bvTTo9IA/view?usp=drivesdk', 'seed', 2),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'STILL LIFE OVERVIEW', 'View PDF', 'drive', 'https://drive.google.com/file/d/1m3ol_-wYTBTzxAg8cSpUKoQhhsWcSQel/view?usp=drivesdk', 'seed', 3),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'Location', 'Shoot addresses & navigation', 'drive', 'https://project-hub-zegna-ss27.pages.dev/locations.html', 'seed', 4),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'Contact List', 'Production team · PDF', 'drive', 'https://project-hub-zegna-ss27.pages.dev/documents/contact-list-zegna-ss27.pdf?v=20260915', 'seed', 5),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'C41 Website', 'Production company', 'drive', 'https://www.c41.eu/', 'seed', 6),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'Accommodation', 'Addresses & directions', 'drive', 'https://project-hub-zegna-ss27.pages.dev/accommodation.html', 'seed', 7),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'document', 'VIP Lunches&Dinners', 'Coming soon', 'drive', 'https://project-hub-zegna-ss27.pages.dev/documents/vip-coming-soon.pdf', 'seed', 8);

INSERT INTO documents (project_id, section, title, source_type, drive_url, entry_date, location, uploader_name, sort_order) VALUES
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'callsheet', 'Day 1 Callsheet', 'drive', 'https://drive.google.com/file/d/1Qdz_VmMHrrmQZfxrTIpQWD4c9FsoTMFk/view?usp=drivesdk', '2026-09-17', 'CA GIANIN', 'seed', 0),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'callsheet', 'Day 2 Callsheet', 'drive', 'https://drive.google.com/file/d/1UX0BJ5hBCzJjj0RGa5ilKwv0cKUqre2l/view?usp=drivesdk', '2026-09-18', 'MOLO DOMASO', 'seed', 1),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'callsheet', 'Day 3 Callsheet', 'drive', 'https://drive.google.com/file/d/1t-_DNdxvA4iRa8nlSHMMT1LqxoEQowjH/view?usp=drivesdk', '2026-09-19', 'MOLO DOMASO', 'seed', 2);

INSERT INTO documents (project_id, section, title, source_type, drive_url, entry_date, uploader_name, sort_order) VALUES
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'menu', 'Brand Ambassador Menu — 17 Sep', 'drive', 'https://project-hub-zegna-ss27.pages.dev/documents/menu-brand-ambassador-17-september-2026.pdf', '2026-09-17', 'seed', 0),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'menu', 'Brand Ambassador Menu — 18 Sep', 'drive', 'https://project-hub-zegna-ss27.pages.dev/documents/menu-brand-ambassador-18-september-2026.pdf', '2026-09-18', 'seed', 1),
    ((SELECT id FROM projects WHERE slug = 'zegna-ss27'), 'menu', 'Brand Ambassador Menu — 19 Sep', 'drive', 'https://project-hub-zegna-ss27.pages.dev/documents/menu-brand-ambassador-19-september-2026.pdf', '2026-09-19', 'seed', 2);
