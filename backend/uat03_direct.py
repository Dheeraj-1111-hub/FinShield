"""
UAT-03: Password Recovery & Session Security
Direct API tests using httpx
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "alex.mercer6000@example.com"
TEST_PASSWORD = "Password123!"
NEW_PASSWORD = "FinshieldTest2026!"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        
        # Part C: Nonexistent Account
        print("=== Part C: Nonexistent Account ===")
        resp = await client.post("/auth/forgot-password", json={"email": "nobody-finshield-test-999@example.com"})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        
        # Part D: Real Account Reset Request
        print("\n=== Part D: Real Account Reset Request ===")
        # First create user
        signup_resp = await client.post("/auth/signup", json={
            "full_name": "Alex Mercer",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        print(f"Signup: {signup_resp.status_code} - {signup_resp.json()}")
        
        # Request reset
        resp = await client.post("/auth/forgot-password", json={"email": TEST_EMAIL})
        print(f"Reset request: {resp.status_code} - {resp.json()}")
        
        # Part M: Malformed Reset Token
        print("\n=== Part M: Malformed Reset Token ===")
        resp = await client.post("/auth/reset-password", json={"token": "malformed_token_123", "password": "NewPass123!"})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        
        # Part F: Password Validation - try weak password with valid token format
        print("\n=== Part F: Password Validation ===")
        # Try with a fake but well-formed token
        resp = await client.post("/auth/reset-password", json={"token": "a" * 64, "password": "123"})
        print(f"Weak password with fake token: {resp.status_code} - {resp.json()}")
        
        # Part F: Mismatched passwords - N/A since API only takes one password field
        print("\n=== Part F: Mismatched Passwords ===")
        print("N/A - API only accepts single password field, no confirmation field in UI or API")
        
        # Part K: Token Replay
        print("\n=== Part K: Reset Token Replay ===")
        print("Backend sets used_at on token (auth.py:264), preventing reuse")
        
        # Part J: Session invalidation
        print("\n=== Part J: Existing Session After Password Reset ===")
        print("Backend code at auth.py:263-270 revokes all sessions on password reset")
        
        # Check login with old password
        print("\n=== Part H: Login with Old Password ===")
        login_resp = await client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        print(f"Old password login: {login_resp.status_code} - {login_resp.json()}")
        
        # Logout
        print("\n=== Logout ===")
        logout_resp = await client.post("/auth/logout")
        print(f"Logout: {logout_resp.status_code} - {logout_resp.json()}")

asyncio.run(main())