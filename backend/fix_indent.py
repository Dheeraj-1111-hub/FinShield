import sys; sys.stdout.reconfigure(encoding='utf-8')
with open('app/api/routes/agent_runtime.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if line.strip() == 'dlog(f"Exception: {str(e)}")':
        prev_indent = len(new_lines[-1]) - len(new_lines[-1].lstrip())
        new_lines.append((' ' * (prev_indent + 4)) + line.lstrip() + '\n')
    else:
        new_lines.append(line)

with open('app/api/routes/agent_runtime.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Done fixing")
