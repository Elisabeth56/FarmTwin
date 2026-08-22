"""Look up a chunk by ID. Run: python scripts/show_chunk.py 10"""
import sys
import sqlite3

if len(sys.argv) < 2:
    print("Usage: python scripts/show_chunk.py <chunk_id> [<chunk_id> ...]")
    sys.exit(1)

conn = sqlite3.connect("backend/farmtwin.db")
for arg in sys.argv[1:]:
    try:
        cid = int(arg)
    except ValueError:
        print(f"skip: {arg} is not a number")
        continue
    row = conn.execute(
        "SELECT id, source_org, chunk_title, content FROM document_chunks WHERE id = ?",
        (cid,)
    ).fetchone()
    if row:
        print(f"\n{'='*70}")
        print(f"CHUNK {row[0]} — {row[1]} — {row[2]}")
        print('='*70)
        print(row[3])
    else:
        print(f"No chunk with id {cid}")
conn.close()

