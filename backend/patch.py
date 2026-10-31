import sys; sys.stdout.reconfigure(encoding='utf-8')
with open('app/api/routes/agent_runtime.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
# Insert a log function at the top of run_deterministic_agent
log_func = '''
    def dlog(msg):
        with open("agent_debug.log", "a") as lf:
            lf.write(msg + "\\n")
'''

content = content.replace('async def run_deterministic_agent(run_id: str, workspace_id: str):',
'async def run_deterministic_agent(run_id: str, workspace_id: str):\n' + log_func)

content = content.replace('try:\n        async for db in get_db():',
'dlog(f"Start run {run_id}")\n    try:\n        async for db in get_db():\n            dlog("Got db session")')

content = content.replace('client = AsyncGroq(api_key=groq_api_key.strip())',
'dlog(f"Groq iteration {iteration}")\n            client = AsyncGroq(api_key=groq_api_key.strip())')

content = content.replace('response = await client.chat.completions.create(',
'dlog("Awaiting groq...")\n                response = await client.chat.completions.create(')

content = content.replace('message = response.choices[0].message',
'dlog("Got groq response")\n                message = response.choices[0].message')

content = content.replace('await AgentRuntimeService.finish_run(',
'dlog("Calling finish_run")\n                    await AgentRuntimeService.finish_run(')

content = content.replace('except Exception as e:',
'except Exception as e:\n        dlog(f"Exception: {str(e)}")')

with open('app/api/routes/agent_runtime.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched agent_runtime.py with dlog')
