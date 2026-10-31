"""
UAT-03: Session Invalidation Test (Part J) - Fixed
"""
import asyncio
import httpx
import sys
import os
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.security import generate_session_token, hash_session_token
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.future import select
from app.models.auth_token import AuthToken, AuthTokenType
from app.models.user import User
from app.models.session import Session

BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "alex.mercer6000@example.com"
TEST_PASSWORD = "Password123!"  # Reset back to original
NEW_PASSWORD = "FinshieldTest2026!"

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///./finshield.db", echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # Find the user
        result = await db.execute(select(User).where(User.email == TEST_EMAIL))
        user = result.scalars().first()
        if not user:
            print(f"User {TEST_EMAIL} not found")
            return
        
        # First, reset password back to original using a direct DB update
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user.password_hash = pwd_context.hash(TEST_PASSWORD)
        await db.commit()
        print(f"Reset password back to original for {TEST_EMAIL}")
        
        # Generate a real reset token for the NEW password
        reset_token = generate_session_token()
        token_hash = hash_session_token(reset_token)
        
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
        
        print(f"Generated reset token for new password")
        
        # Create two separate HTTP clients (simulating two browser sessions)
        print("\n=== Part J: Existing Session After Password Reset ===")
        
        # Session A: Login and keep authenticated
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client_a:
            login_a = await client_a.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
            print(f"Browser A login: {login_a.status_code}")
            cookie_a = dict(client_a.cookies).get('finshield_session', 'N/A')
            print(f"Browser A session cookie: {cookie_a[:20] if cookie_a != 'N/A' else 'N/A'}...")
            
            # Verify session A is valid
            me_a = await client_a.get("/auth/me")
            print(f"Browser A /auth/me before reset: {me_a.status_code}")
            
            # Session B: Login and keep authenticated
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client_b:
                login_b = await client_b.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
                print(f"Browser B login: {login_b.status_code}")
                cookie_b = dict(client_b.cookies).get('finshield_session', 'N/A')
                print(f"Browser B session cookie: {cookie_b[:20] if cookie_b != 'N/A' else 'N/A'}...")
                
                # Verify session B is valid
                me_b = await client_b.get("/auth/me")
                print(f"Browser B /auth/me before reset: {me_b.status_code}")
            
            # Now perform password reset (using the token we generated)
            print("\n--- Performing password reset ---")
            reset_resp = await client_a.post("/auth/reset-password", json={"token": reset_token, "password": NEW_PASSWORD})
            print(f"Password reset: {reset_resp.status_code} - {reset_resp.json()}")
            
            # Check if session A still works
            print("\n--- Checking sessions after password reset ---")
            me_a_after = await client_a.get("/auth/me")
            print(f"Browser A /auth/me after reset: {me_a_after.status_code}")
            if me_a_after.status_code == 200:
                print("  Session A STILL ACTIVE - sessions NOT invalidated after password reset")
            else:
                print("  Session A INVALIDATED - sessions revoked after password reset")
            
            # Check if session B still works
            async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client_b_check:
                # Set the cookie from session B
                if cookie_b != 'N/A':
                    client_b_check.cookies.set('finshield_session', cookie_b, domain='localhost')
                    me_b_after = await client_b_check.get("/auth/me")
                    print(f"Browser B /auth/me after reset: {me_b_after.status_code}")
                    if me_b_after.status_code == 200:
                        print("  Session B STILL ACTIVE - sessions NOT invalidated after password reset")
                    else:
                        print("  Session B INVALIDATED - sessions revoked after password reset")
                else:
                    print("  Could not check session B - no cookie")
            
            # Check database for session revocation
            print("\n--- Database session status ---")
            result = await db.execute(select(Session).where(Session.user_id == user.id, Session.revoked_at.isnot(None)))
            sessions = result.scalars().all()
            print(f"  Revoked sessions: {len(sessions)}")
            for s in sessions:
                print(f"    Session {s.id[:12]}... revoked_at: {s.revoked_at}")

asyncio.run(main())