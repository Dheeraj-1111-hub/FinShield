import asyncio
import httpx

async def run_tests():
    async with httpx.AsyncClient() as client:
        # Create a workspace, agent, etc. to actually test it.
        # But wait, without authentication, how do we do that?
        # The backend requires valid session tokens or API keys. 
        # I will try fetching from public endpoints if any, or just test an endpoint to see if it's 401.
        try:
            res = await client.get("http://127.0.0.1:8000/api/v1/workspaces")
            print("GET workspaces:", res.status_code, res.text)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(run_tests())
