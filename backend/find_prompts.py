import json

with open(r'C:\Users\Sai Dheeraj\.gemini\antigravity-ide\brain\1fc7db8b-c077-44ea-a78c-00642ccf1edf\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get('type') == 'USER_INPUT':
            content = data.get('content', '')
            print(f"=== Step {data.get('step_index')} ===")
            print(content[:300].encode('ascii', 'replace').decode('ascii'))
            print()
