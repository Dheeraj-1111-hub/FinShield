import sqlite3
conn = sqlite3.connect('finshield.db')
conn.execute("UPDATE products SET category='Hardware' WHERE category='laptop'")
conn.commit()
conn.close()
