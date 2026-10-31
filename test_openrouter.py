import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
import json

# Load environment variables
load_dotenv(os.path.join(r"C:\Users\Sai Dheeraj\OneDrive\Desktop\Main_Projects\finshield\backend", ".env"))

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("Error: OPENROUTER_API_KEY not found in environment.")
    sys.exit(1)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

model = "nvidia/nemotron-3-ultra-550b-a55b:free"

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Fetch details about a specific product by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The unique identifier of the product",
                    }
                },
                "required": ["product_id"],
            },
        },
    }
]

messages = [{"role": "user", "content": "Find product LAPTOP-001 and use the get_product tool."}]

try:
    print(f"Requesting tool call from {model}...")
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        max_tokens=200
    )

    message = response.choices[0].message
    finish_reason = response.choices[0].finish_reason

    print("\n--- API Success ---")
    print(f"Model Used: {response.model}")
    print(f"Finish Reason: {finish_reason}")

    if message.tool_calls:
        print("\n--- Tool Call Detected ---")
        for tool_call in message.tool_calls:
            print(f"Tool Name: {tool_call.function.name}")
            print(f"Arguments: {tool_call.function.arguments}")
        
        # Verify the arguments are parsed correctly
        args = json.loads(message.tool_calls[0].function.arguments)
        if "product_id" in args:
            print("\nSuccessfully extracted tool call. Test PASSED.")
            sys.exit(0)
        else:
            print("\nTool call arguments missing 'product_id'. Test FAILED.")
            sys.exit(1)
    else:
        print("\nNo tool calls were made by the model. Test FAILED.")
        print(f"Model Content: {message.content}")
        sys.exit(1)

except Exception as e:
    print(f"\nAPI Error / Failure: {e}")
    sys.exit(1)
