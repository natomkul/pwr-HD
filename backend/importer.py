import os
import psycopg2
from dotenv import load_dotenv
from parser import parsuj_plik_bib

load_dotenv()

DB_CONFIG = {
    'host':     os.getenv('DB_HOST'),
    'port':     int(os.getenv('DB_PORT', '5432')),
    'dbname':   os.getenv('DB_NAME'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
}


def _insert_entry(cur, entry):
    year = None
    if entry.get('year'):
        try:
            # Take only the leading digits in case of values like "2023a"
            year = int(str(entry['year'])[:4])
        except (ValueError, TypeError):
            pass

    cur.execute(
        """
        INSERT INTO entries (bib_key, bib_type, title, year, publisher, journal)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (bib_key) DO UPDATE SET
            bib_type  = EXCLUDED.bib_type,
            title     = EXCLUDED.title,
            year      = EXCLUDED.year,
            publisher = EXCLUDED.publisher,
            journal   = EXCLUDED.journal
        RETURNING id
        """,
        (
            entry['bib_key'],
            entry['bib_type'],
            entry.get('title'),
            year,
            entry.get('publisher'),
            entry.get('journal'),
        ),
    )
    return cur.fetchone()[0]


def _insert_author(cur, author):
    first = author.get('first_name') or ''
    last  = author.get('last_name')  or ''
    cur.execute(
        """
        INSERT INTO authors (first_name, last_name)
        VALUES (%s, %s)
        ON CONFLICT (first_name, last_name) DO UPDATE SET last_name = EXCLUDED.last_name
        RETURNING id
        """,
        (first, last),
    )
    return cur.fetchone()[0]


def _link_author(cur, entry_id, author_id, order):
    cur.execute(
        """
        INSERT INTO entry_authors (entry_id, author_id, author_order)
        VALUES (%s, %s, %s)
        ON CONFLICT (entry_id, author_id) DO UPDATE SET author_order = EXCLUDED.author_order
        """,
        (entry_id, author_id, order),
    )


def import_entries(conn, entries):
    with conn.cursor() as cur:
        for entry in entries:
            entry_id = _insert_entry(cur, entry)
            for order, author in enumerate(entry.get('author') or [], start=1):
                author_id = _insert_author(cur, author)
                _link_author(cur, entry_id, author_id, order)
    conn.commit()


if __name__ == '__main__':
    bib_file = os.getenv('BIB_FILE', 'AI.bib')
    print(f"Parsing {bib_file} ...")
    entries = parsuj_plik_bib(bib_file)
    print(f"  Found {len(entries)} entries.")

    print("Connecting to database ...")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        import_entries(conn, entries)
        print(f"  Inserted/updated {len(entries)} entries into the database.")
    finally:
        conn.close()
