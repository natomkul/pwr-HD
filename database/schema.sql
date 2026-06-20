-- Bibliography Management Database Schema
-- Based on parser.py structure

CREATE TABLE entries (
    id          SERIAL PRIMARY KEY,
    bib_key     VARCHAR(255)    NOT NULL UNIQUE,
    bib_type    VARCHAR(50)     NOT NULL,
    title       TEXT,
    year        SMALLINT,
    publisher   TEXT,
    journal     TEXT
);

CREATE TABLE authors (
    id          SERIAL PRIMARY KEY,
    first_name  VARCHAR(255)    NOT NULL DEFAULT '',
    last_name   VARCHAR(255)    NOT NULL,
    UNIQUE (first_name, last_name)
);

-- Junction table preserving author order within an entry
CREATE TABLE entry_authors (
    entry_id        INTEGER     NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    author_id       INTEGER     NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    author_order    SMALLINT    NOT NULL,
    PRIMARY KEY (entry_id, author_id)
);

-- Indexes for common lookups
CREATE INDEX idx_entries_bib_type    ON entries (bib_type);
CREATE INDEX idx_entries_year        ON entries (year);
CREATE INDEX idx_entries_title       ON entries USING gin (to_tsvector('english', coalesce(title, '')));
CREATE INDEX idx_authors_last_name   ON authors (last_name);
CREATE INDEX idx_entry_authors_entry ON entry_authors (entry_id);
CREATE INDEX idx_entry_authors_author ON entry_authors (author_id);
