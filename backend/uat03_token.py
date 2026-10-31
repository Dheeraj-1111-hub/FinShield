"""
UAT-03: Full E2E test with token capture
"""
import asyncio
import httpx
import subprocess
import sys
import os
import re

BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "alex.mercer6000@example.com"
TEST_PASSWORD = "Password123!"
NEW_PASSWORD = "FinshieldTest2026!"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        
        # First, let's login to get a session cookie
        print("=== Login with existing credentials ===")
        login_resp = await client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        print(f"Login: {login_resp.status_code} - {login_resp.json()}")
        
        # Get the session cookie
        cookies = client.cookies
        print(f"Session cookie: {dict(cookies)}")
        
        # Now request password reset - this will print the token to backend stdout
        print("\n=== Request Password Reset ===")
        resp = await client.post("/auth/forgot-password", json={"email": TEST_EMAIL})
        print(f"Reset request: {resp.status_code} - {resp.json()}")
        
        # The token is printed to the backend process stdout
        # Let's check the backend process logs
        print("\n=== Checking backend logs for reset token ===")
        
        # Try to get the token by querying the database directly
        # Since we can't easily capture stdout, let's use a different approach
        # We'll create a script that the backend can execute to get the token
        
        # Actually, let's just check if the token exists in the DB
        # by trying to reset with various approaches
        
        # Let's try the reset with a real token by reading from the DB
        print("\n=== Attempting to get token from database ===")
        
        # Use sqlite to query the auth_tokens table
        import sqlite3
        db_path = "C:\\Users\\Sai Dheeraj\\OneDrive\Desktop\\Main_Projects\\finshield\\backend\\finshield.db"
        
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT token_hash, type, used_at, expires_at FROM auth_tokens WHERE type = 'RESET' ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                print(f"Token hash: {row[0][:16]}..., Type: {row[1]}, Used: {row[2]}, Expires: {row[3]}")
            else:
                print("No reset token found in DB")
            conn.close()
        else:
            print(f"Database not found at {db_path}")

asyncio.run(main())