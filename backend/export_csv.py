import os
import csv
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host':     os.getenv('DB_HOST'),
    'port':     int(os.getenv('DB_PORT', '5432')),
    'dbname':   os.getenv('DB_NAME'),
    'user':     os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
}

# Flat query — one row per entry, authors as a semicolon-separated string.
# utf-8-sig (UTF-8 with BOM) is required so Power BI / Excel auto-detects the encoding.
QUERY = """
SELECT
    e.bib_key,
    e.bib_type,
    e.title,
    e.year,
    e.publisher,
    e.journal,
    STRING_AGG(
        CASE
            WHEN a.first_name <> '' THEN a.first_name || ' ' || a.last_name
            ELSE a.last_name
        END,
        '; ' ORDER BY ea.author_order
    ) AS authors
FROM entries e
LEFT JOIN entry_authors ea ON ea.entry_id = e.id
LEFT JOIN authors        a  ON a.id = ea.author_id
GROUP BY e.id
ORDER BY e.year DESC NULLS LAST, e.bib_key;
"""


if __name__ == '__main__':
    output_path = os.getenv('CSV_OUTPUT', 'output/bibliography.csv')
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    print("Connecting to database ...")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY)
            rows    = cur.fetchall()
            headers = [desc[0] for desc in cur.description]
    finally:
        conn.close()

    # utf-8-sig writes a UTF-8 BOM at the start of the file,
    # which is the encoding Power BI and Excel expect for reliable CSV import.
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Exported {len(rows)} rows -> {output_path}")
