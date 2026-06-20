import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

load_dotenv()

DB_CONFIG = {
    'host':     os.getenv('DB_HOST'),
    'port':     int(os.getenv('DB_PORT', '5432')),
    'dbname':   os.getenv('DB_NAME'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
}

UPDATABLE_FIELDS = {'bib_type', 'title', 'year', 'publisher', 'journal'}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


app = FastAPI(title="Bibliography Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Author(BaseModel):
    first_name: str = ""
    last_name: str


class EntryCreate(BaseModel):
    bib_key: str
    bib_type: str
    title: Optional[str] = None
    year: Optional[int] = None
    publisher: Optional[str] = None
    journal: Optional[str] = None
    authors: list[Author] = []


class EntryUpdate(BaseModel):
    bib_type: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    publisher: Optional[str] = None
    journal: Optional[str] = None
    authors: Optional[list[Author]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENTRY_SELECT = """
    SELECT
        e.id, e.bib_key, e.bib_type, e.title, e.year, e.publisher, e.journal,
        COALESCE(
            JSON_AGG(
                JSON_BUILD_OBJECT('first_name', a.first_name, 'last_name', a.last_name)
                ORDER BY ea.author_order
            ) FILTER (WHERE a.id IS NOT NULL),
            '[]'
        ) AS authors
    FROM entries e
    LEFT JOIN entry_authors ea ON ea.entry_id = e.id
    LEFT JOIN authors a ON a.id = ea.author_id
"""


def _sync_authors(cur, entry_id: int, authors: list[Author]):
    cur.execute("DELETE FROM entry_authors WHERE entry_id = %s", (entry_id,))
    for order, author in enumerate(authors, start=1):
        first = author.first_name or ''
        last  = author.last_name  or ''
        cur.execute(
            """
            INSERT INTO authors (first_name, last_name)
            VALUES (%s, %s)
            ON CONFLICT (first_name, last_name) DO UPDATE SET last_name = EXCLUDED.last_name
            RETURNING id
            """,
            (first, last),
        )
        author_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO entry_authors (entry_id, author_id, author_order) VALUES (%s, %s, %s)",
            (entry_id, author_id, order),
        )


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/entries")
def list_entries():
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                _ENTRY_SELECT + " GROUP BY e.id ORDER BY e.year DESC NULLS LAST, e.bib_key"
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


@app.get("/api/entries/{entry_id}")
def get_entry(entry_id: int):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                _ENTRY_SELECT + " WHERE e.id = %s GROUP BY e.id",
                (entry_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Entry not found")
            return dict(row)
    finally:
        conn.close()


@app.post("/api/entries", status_code=201)
def create_entry(entry: EntryCreate):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO entries (bib_key, bib_type, title, year, publisher, journal)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (entry.bib_key, entry.bib_type, entry.title,
                 entry.year, entry.publisher, entry.journal),
            )
            entry_id = cur.fetchone()[0]
            _sync_authors(cur, entry_id, entry.authors)
        conn.commit()
        return {"id": entry_id}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="bib_key already exists")
    finally:
        conn.close()


@app.put("/api/entries/{entry_id}")
def update_entry(entry_id: int, entry: EntryUpdate):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM entries WHERE id = %s", (entry_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Entry not found")

            # Only update fields that are explicitly provided and in the whitelist
            fields = {
                k: v for k, v in entry.model_dump(exclude={'authors'}).items()
                if v is not None and k in UPDATABLE_FIELDS
            }
            if fields:
                set_clause = ", ".join(f"{col} = %s" for col in fields)
                cur.execute(
                    f"UPDATE entries SET {set_clause} WHERE id = %s",
                    (*fields.values(), entry_id),
                )

            if entry.authors is not None:
                _sync_authors(cur, entry_id, entry.authors)

        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@app.delete("/api/entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM entries WHERE id = %s RETURNING id", (entry_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Entry not found")
        conn.commit()
    finally:
        conn.close()


# Must be last — catches all remaining routes as static files
app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="static")
