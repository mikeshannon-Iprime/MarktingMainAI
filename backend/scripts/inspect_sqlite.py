import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "marketingmind.db"
conn = sqlite3.connect(db)
cur = conn.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print("TABLES:", [t[0] for t in tables])
for (name,) in tables:
    cols = cur.execute(f"PRAGMA table_info({name})").fetchall()
    count = cur.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    print(f"\n{name} ({count} rows):")
    for c in cols:
        print(f"  {c[1]} {c[2]}")
    if count and count <= 5:
        rows = cur.execute(f"SELECT * FROM {name} LIMIT 5").fetchall()
        for row in rows:
            print("  ", row)
conn.close()
