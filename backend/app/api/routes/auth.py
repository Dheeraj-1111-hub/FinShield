from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta
import uuid

from app.db.database import get_db
from app.models.audit import EventTypes
from app.models.user import User, UserStatus
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.session import Session
from app.models.auth_token import AuthToken, AuthTokenType
from app.models.auth_event import AuthEvent
from app.core.security import get_password_hash, verify_password, generate_session_token, hash_session_token
from app.core.dependencies import get_current_user, get_current_workspace
from app.services.commerce_init_service import initialize_sandbox_catalog
from app.core.rate_limit import limiter
from pydantic import BaseModel, EmailStr, field_validator
import re

router = APIRouter()

_MOCK_INBOX = []

class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one number')
        if not any(char.isalpha() for char in v):
            raise ValueError('Password must contain at least one letter')
        return v

class VerifyEmailRequest(BaseModel):
    token: str

def set_cookie(response: Response, token: str):
    response.set_cookie(
        key='finshield_session',
        value=token,
        httponly=True,
        secure=False,  # Set to True in production
        samesite='lax',
        max_age=30 * 24 * 60 * 60, # 30 days
        path='/'
    )

async def log_auth_event(db: AsyncSession, event_type: str, user_id: str | None, request: Request, workspace_id: str | None = None):
    from app.services.audit_service import AuditService
    from app.models.audit import EventCategory, EventSeverity, ActorType, EventTypes
    
    ip_metadata = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # If workspace_id is not provided, try to find one for the user
    if not workspace_id and user_id:
        result = await db.execute(select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id).limit(1))
        workspace_id = result.scalar_one_or_none()
        
    if workspace_id:
        audit_service = AuditService(db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type=event_type,
            event_category=EventCategory.AUTH,
            severity=EventSeverity.INFO if "FAILED" not in event_type else EventSeverity.WARNING,
            actor_type=ActorType.USER if user_id else ActorType.SYSTEM,
            actor_id=user_id,
            metadata={"ip_address": ip_metadata, "user_agent": user_agent}
        )
    else:
        # Fallback to old AuthEvent if no workspace exists yet (e.g. invalid login for non-existent user)
        event = AuthEvent(
            id='evt_' + uuid.uuid4().hex[:12],
            user_id=user_id,
            event_type=event_type,
            ip_metadata=ip_metadata,
            user_agent=user_agent
        )
        db.add(event)

@router.post('/signup')
@limiter.limit("5/minute")
async def signup(request: Request, req: SignupRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail='Email already exists')
        
    user_id = 'usr_' + uuid.uuid4().hex[:12]
    user = User(
        id=user_id,
        email=req.email.lower(),
        password_hash=get_password_hash(req.password),
        full_name=req.full_name,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    
    workspace_id = 'wksp_' + uuid.uuid4().hex[:12]
    workspace = Workspace(
        id=workspace_id,
        name=f"{req.full_name}'s Workspace",
        slug=workspace_id.replace('_', '-'),
        owner_id=user_id
    )
    db.add(workspace)
    
    member_id = 'mem_' + uuid.uuid4().hex[:12]
    member = WorkspaceMember(
        id=member_id,
        workspace_id=workspace_id,
        user_id=user_id,
        role=WorkspaceRole.OWNER
    )
    db.add(member)
    
    # Generate verification token
    v_token = generate_session_token()
    auth_token = AuthToken(
        id='atk_' + uuid.uuid4().hex[:12],
        user_id=user_id,
        token_hash=hash_session_token(v_token),
        type=AuthTokenType.VERIFICATION,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db.add(auth_token)
    
    token = generate_session_token()
    session_id = 'sess_' + uuid.uuid4().hex[:12]
    session = Session(
        id=session_id,
        user_id=user_id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(session)
    
    
    # Initialize sandbox catalog for the new workspace
    await initialize_sandbox_catalog(db, workspace_id)
    
    









    







    await log_auth_event(db, EventTypes.USER_REGISTERED, user_id, request, workspace_id)
    await db.commit()
    
    # Mock sending email
    print(f"[MOCK EMAIL] Verification token for {user.email}: {v_token}")
    
    set_cookie(response, token)
    
    return {
        'user': {'id': user.id, 'email': user.email, 'full_name': user.full_name},
        'workspace': {'id': workspace.id, 'name': workspace.name}
    }

@router.post('/login')
@limiter.limit("5/minute")
async def login(request: Request, req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    from app.models.audit import EventTypes
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalars().first()
    
    if not user or not verify_password(req.password, user.password_hash):
        await log_auth_event(db, EventTypes.USER_LOGIN_FAILED, user.id if user else None, request)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
        
    if user.status != UserStatus.ACTIVE:
        await log_auth_event(db, EventTypes.USER_LOGIN_FAILED, user.id, request)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account is disabled')
        
    user.last_login_at = datetime.now(timezone.utc)
    
    token = generate_session_token()
    session_id = 'sess_' + uuid.uuid4().hex[:12]
    session = Session(
        id=session_id,
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(session)
    
    await log_auth_event(db, EventTypes.USER_LOGIN_SUCCEEDED, user.id, request)
    await db.commit()
    
    set_cookie(response, token)
    return {'message': 'Logged in successfully'}

@router.post('/logout')
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from app.models.audit import EventTypes
    session_token = request.cookies.get('finshield_session')
    if session_token:
        token_hash = hash_session_token(session_token)
        result = await db.execute(select(Session).where(Session.token_hash == token_hash))
        session = result.scalars().first()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            await log_auth_event(db, EventTypes.USER_LOGOUT, session.user_id, request)
            await db.commit()
            
    response.delete_cookie('finshield_session')
    return {'message': 'Logged out successfully'}

@router.get('/me')
async def get_me(user: User = Depends(get_current_user), workspace: Workspace = Depends(get_current_workspace)):
    return {
        'user': {'id': user.id, 'email': user.email, 'full_name': user.full_name},
        'workspace': {'id': workspace.id, 'name': workspace.name, 'currency': workspace.currency}
    }

@router.post('/forgot-password')
@limiter.limit("3/minute")
async def forgot_password(request: Request, req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    from app.models.audit import EventTypes
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalars().first()
    
    # Always return success to prevent email enumeration
    if user:
        reset_token = generate_session_token()
        auth_token = AuthToken(
            id='atk_' + uuid.uuid4().hex[:12],
            user_id=user.id,
            token_hash=hash_session_token(reset_token),
            type=AuthTokenType.RESET,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db.add(auth_token)
        await log_auth_event(db, EventTypes.PASSWORD_RESET_REQUESTED, user.id, request)
        await db.commit()
        
        # Mock sending email
        print(f"[MOCK EMAIL] Password reset token for {user.email}: {reset_token}")
        from app.core.config import settings
        if settings.ENVIRONMENT in ["local", "development", "test"]:
            _MOCK_INBOX.append({
                "to": user.email,
                "subject": "Password Reset",
                "body": f"Click here to reset your password: http://localhost:8080/reset-password?token={reset_token}",
                "token": reset_token,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
    return {'message': 'If an account with that email exists, we have sent a password reset link.'}

@router.get('/dev/inbox')
async def get_dev_inbox():
    from app.core.config import settings
    if settings.ENVIRONMENT not in ["local", "development", "test"]:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"inbox": _MOCK_INBOX}

@router.delete('/dev/inbox')
async def clear_dev_inbox():
    from app.core.config import settings
    if settings.ENVIRONMENT not in ["local", "development", "test"]:
        raise HTTPException(status_code=404, detail="Not Found")
    _MOCK_INBOX.clear()
    return {"message": "Inbox cleared"}

@router.post('/reset-password')
@limiter.limit("3/minute")
async def reset_password(request: Request, req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    from app.models.audit import EventTypes
    token_hash = hash_session_token(req.token)
    result = await db.execute(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.type == AuthTokenType.RESET,
            AuthToken.used_at == None,
            AuthToken.expires_at > datetime.now(timezone.utc)
        )
    )
    auth_token = result.scalars().first()
    
    if not auth_token:
        raise HTTPException(status_code=400, detail='Invalid or expired reset token')
        
    result = await db.execute(select(User).where(User.id == auth_token.user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail='User not found')
        
    # Update password
    user.password_hash = get_password_hash(req.password)
    auth_token.used_at = datetime.now(timezone.utc)
    
    # Revoke all existing sessions
    result = await db.execute(select(Session).where(Session.user_id == user.id, Session.revoked_at == None))
    sessions = result.scalars().all()
    for session in sessions:
        session.revoked_at = datetime.now(timezone.utc)
        
    await log_auth_event(db, EventTypes.PASSWORD_RESET_COMPLETED, user.id, request)
    await db.commit()
    
    return {'message': 'Password has been reset successfully. Please log in with your new password.'}

@router.post('/verify-email')
@limiter.limit("5/minute")
async def verify_email(request: Request, req: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    from app.models.audit import EventTypes
    token_hash = hash_session_token(req.token)
    result = await db.execute(
        select(AuthToken).where(
            AuthToken.token_hash == token_hash,
            AuthToken.type == AuthTokenType.VERIFICATION,
            AuthToken.used_at == None
        )
    )
    auth_token = result.scalars().first()
    
    if not auth_token:
        raise HTTPException(status_code=400, detail='Invalid verification token')
        
    result = await db.execute(select(User).where(User.id == auth_token.user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail='User not found')
        
    user.email_verified_at = datetime.now(timezone.utc)
    auth_token.used_at = datetime.now(timezone.utc)
    
    await log_auth_event(db, EventTypes.EMAIL_VERIFIED, user.id, request)
    await db.commit()
    
    return {'message': 'Email has been verified successfully.'}
