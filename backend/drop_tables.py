import sqlite3

conn = sqlite3.connect('finshield.db')
cursor = conn.cursor()

tables = [
    'investigation_evidence',
    'investigation_notes',
    'investigation_timeline_events',
    'investigations',
    'security_events'
]

for table in tables:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    except Exception as e:
        print(f"Failed to drop {table}: {e}")

conn.commit()
conn.close()
print("Done")
