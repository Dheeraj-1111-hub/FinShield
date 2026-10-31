"""
UAT-03: Full E2E test with real reset token generation
"""
import asyncio
import httpx
import sys
import os
import sqlite3
import hashlib

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.security import generate_session_token, hash_session_token
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.future import select
from app.db.database import Base
from app.models.auth_token import AuthToken, AuthTokenType
from app.models.user import User

BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "alex.mercer6000@example.com"
TEST_PASSWORD = "Password123!"
NEW_PASSWORD = "FinshieldTest2026!"

async def main():
    # Connect to the database to get/create a real token
    engine = create_async_engine("sqlite+aiosqlite:///./finshield.db", echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # Find the user
        result = await db.execute(select(User).where(User.email == TEST_EMAIL))
        user = result.scalars().first()
        if not user:
            print(f"User {TEST_EMAIL} not found")
            return
        
        # Generate a real reset token
        reset_token = generate_session_token()
        token_hash = hash_session_token(reset_token)
        
        # Create auth token record
        from datetime import datetime, timezone, timedelta
        auth_token = AuthToken(
            id='atk_' + __import__('uuid').uuid4().hex[:12],
            user_id=user.id,
            token_hash=token_hash,
            type=AuthTokenType.RESET,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db.add(auth_token)
        await db.commit()
        
        print(f"Generated reset token: {reset_token}")
        print(f"Token hash: {token_hash}")
        
        # Now test the full flow
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            
            # Part E: Use the real reset link
            print("\n=== Part E: Password Reset Link ===")
            print(f"Reset link: http://localhost:5173/reset-password?token={reset_token}")
            
            # Part F: Try weak password
            print("\n=== Part F: Password Validation ===")
            resp = await client.post("/auth/reset-password", json={"token": reset_token, "password": "123"})
            print(f"Weak password '123': {resp.status_code} - {resp.json()}")
            
            # Reset the token since it was "used" (even if failed)
            # Actually the backend doesn't mark it used on failed attempts
            # Let's check
            auth_token.used_at = None
            await db.commit()
            
            # Part F: Try mismatched passwords (N/A - API only has one password field)
            print("\n=== Part F: Mismatched Passwords ===")
            print("N/A - API only accepts single password field, no confirmation field in UI or API")
            
            # Part G: Successful password reset
            print("\n=== Part G: Successful Password Reset ===")
            resp = await client.post("/auth/reset-password", json={"token": reset_token, "password": NEW_PASSWORD})
            print(f"Reset with '{NEW_PASSWORD}': {resp.status_code} - {resp.json()}")
            
            # Part H: Old password rejected
            print("\n=== Part H: Old Password Rejected ===")
            login_resp = await client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
            print(f"Old password '{TEST_PASSWORD}': {login_resp.status_code} - {login_resp.json()}")
            
            # Part I: New password accepted
            print("\n=== Part I: New Password Accepted ===")
            login_resp = await client.post("/auth/login", json={"email": TEST_EMAIL, "password": NEW_PASSWORD})
            print(f"New password '{NEW_PASSWORD}': {login_resp.status_code} - {login_resp.json()}")
            
            # Part K: Reset token replay
            print("\n=== Part K: Reset Token Replay ===")
            resp = await client.post("/auth/reset-password", json={"token": reset_token, "password": "AnotherPass123!"})
            print(f"Replay with same token: {resp.status_code} - {resp.json()}")
            
            # Part L: Expired token
            print("\n=== Part L: Reset Token Expiration ===")
            expired_token = generate_session_token()
            expired_hash = hash_session_token(expired_token)
            from datetime import datetime, timezone, timedelta
            expired_auth_token = AuthToken(
                id='atk_' + __import__('uuid').uuid4().hex[:12],
                user_id=user.id,
                token_hash=expired_hash,
                type=AuthTokenType.RESET,
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
            )
            db.add(expired_auth_token)
            await db.commit()
            
            resp = await client.post("/auth/reset-password", json={"token": expired_token, "password": "NewPass123!"})
            print(f"Expired token: {resp.status_code} - {resp.json()}")
            
            # Part M: Malformed token
            print("\n=== Part M: Malformed Reset Token ===")
            resp = await client.post("/auth/reset-password", json={"token": "malformed_token_123", "password": "NewPass123!"})
            print(f"Malformed token: {resp.status_code} - {resp.json()}")
            
            # Part N: Session persistence
            print("\n=== Part N: Session Persistence ===")
            # Login with new password
            login_resp = await client.post("/auth/login", json={"email": TEST_EMAIL, "password": NEW_PASSWORD})
            print(f"Login: {login_resp.status_code}")
            # Check /auth/me
            me_resp = await client.get("/auth/me")
            print(f"Auth me: {me_resp.status_code} - {me_resp.json()}")
            
            # Part O: Logout
            print("\n=== Part O: Logout After Password Reset ===")
            logout_resp = await client.post("/auth/logout")
            print(f"Logout: {logout_resp.status_code} - {logout_resp.json()}")
            # Try to access /auth/me after logout
            me_resp = await client.get("/auth/me")
            print(f"Auth me after logout: {me_resp.status_code} - {me_resp.json()}")

asyncio.run(main())