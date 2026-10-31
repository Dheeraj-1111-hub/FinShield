import sqlite3
conn = sqlite3.connect('finshield.db')
c = conn.cursor()
print(c.execute("SELECT workspace_id FROM merchants").fetchall())
