"""Quick DB migration — adds v4 columns to predictions table."""
import sqlite3

conn = sqlite3.connect("wildtrack.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(predictions)")
existing = [row[1] for row in cursor.fetchall()]
print("Existing columns:", existing)

additions = [
    ("model_version", "TEXT DEFAULT 'v4'"),
    ("dataset_version", "TEXT DEFAULT 'v1.2-cleaned'"),
    ("accuracy_benchmark", "TEXT"),
    ("is_rejected", "INTEGER DEFAULT 0"),
    ("needs_review", "INTEGER DEFAULT 0"),
]

for col_name, col_type in additions:
    if col_name not in existing:
        sql = f"ALTER TABLE predictions ADD COLUMN {col_name} {col_type}"
        cursor.execute(sql)
        print(f"  Added column: {col_name}")
    else:
        print(f"  Column exists: {col_name}")

conn.commit()
conn.close()
print("Migration complete!")
