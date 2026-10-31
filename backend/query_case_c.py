import sqlite3
import json

conn = sqlite3.connect('finshield.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get the latest protected Case C run
cur.execute("SELECT * FROM benchmark_case_results WHERE case_id='CASE_C_AGENT_SPOOFING' AND is_baseline=0 ORDER BY created_at DESC LIMIT 1")
res = dict(cur.fetchone())

# Print evidence
evidence = json.loads(res['evidence']) if res.get('evidence') and res['evidence'] != 'null' else {}
with open('case_c_evidence.json', 'w', encoding='utf-8') as f:
    json.dump(evidence, f, indent=2)
