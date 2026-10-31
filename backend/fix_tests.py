import os

filepath = "tests/api/test_phase8.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace all occurrences
content = content.replace(
    'headers=owner_ctx["headers"]', 
    'headers=owner_ctx["headers"], cookies=owner_ctx["cookies"]'
)

# For IDOR test specifically
content = content.replace(
    'headers=headers2',
    'headers=headers2, cookies=cookies2'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Replaced headers with headers+cookies successfully.")
