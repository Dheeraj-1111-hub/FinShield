import sqlite3
import json

db_path = 'finshield.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get the AMOUNT_ESCALATION protected result
cursor.execute("""
    SELECT * FROM benchmark_case_results 
    WHERE case_id = 'AMOUNT_ESCALATION' AND is_baseline = 0
    ORDER BY created_at DESC LIMIT 1
""")
result = cursor.fetchone()

if not result:
    print("No AMOUNT_ESCALATION protected result found.")
    exit(1)

print(f"Case ID: {result['case_id']}")
print(f"Run ID: {result['benchmark_run_id']}")
print(f"Execution Status: {result['execution_status']}")
print(f"Gate Decision: {result['gate_decision']}")
print(f"Evidence:")

evidence_str = result['evidence']
if isinstance(evidence_str, str):
    evidence = json.loads(evidence_str)
    if isinstance(evidence, str):
        evidence = json.loads(evidence)

for msg in evidence:
    if isinstance(msg, str):
        try:
            msg = json.loads(msg)
        except:
            pass
    if msg['role'] == 'tool':
        print(f"  TOOL RESULT: {msg['name']}")
        try:
            print(f"  {json.dumps(json.loads(msg['content']), indent=2)}")
        except:
            print(f"  {msg['content']}")
    else:
        print(f"  {msg['role'].upper()}:")
        if 'tool_calls' in msg and msg['tool_calls']:
            for tc in msg['tool_calls']:
                print(f"    CALL {tc['function']['name']}({tc['function']['arguments']})")
        if msg.get('content'):
            print(f"    {msg['content']}")

# Find the run context
cursor.execute("SELECT * FROM agents WHERE name LIKE '%AMOUNT_ESCALATION%' ORDER BY created_at DESC LIMIT 1")
agent = cursor.fetchone()

print("\n--- Agent Data ---")
if agent:
    agent_id = agent['id']
    print(f"Agent ID: {agent_id}")
    
    cursor.execute("SELECT * FROM delegated_authorities WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1", (agent_id,))
    auth = cursor.fetchone()
    if auth:
        print(f"Authority Limit: {auth['monetary_limit']} {auth['currency']}")
        print(f"Approval Threshold: {auth['approval_threshold']}")
    else:
        print("No authority found.")
        
    cursor.execute("SELECT * FROM agent_runs WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1", (agent_id,))
    run = cursor.fetchone()
    if run:
        print(f"Run Intent: {run['intent_context']}")
        
    # Check transactions / orders
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5")
    orders = cursor.fetchall()
    print("\n--- Recent Orders ---")
    for o in orders:
        print(dict(o))
        
    cursor.execute("SELECT * FROM payments ORDER BY created_at DESC LIMIT 5")
    payments = cursor.fetchall()
    print("\n--- Recent Payments ---")
    for p in payments:
        print(dict(p))
        
    cursor.execute("SELECT * FROM agent_actions WHERE agent_run_id = ? ORDER BY created_at ASC", (run['id'],))
    actions = cursor.fetchall()
    print("\n--- Agent Actions / Gate Context ---")
    for a in actions:
        print(dict(a))
else:
    print("Agent not found.")
