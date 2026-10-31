import secrets
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from fastapi import HTTPException
from app.models.developer import ApiCredential, ApiClientStatus, ApiClient

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class DeveloperAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_api_key(self, is_live: bool = False) -> tuple[str, str, str]:
        """Generates a raw secret, its prefix, and its hash. 
        Returns (raw_secret, prefix, hash)
        """
        env_prefix = "fs_live_" if is_live else "fs_test_"
        random_part = secrets.token_urlsafe(32)
        raw_secret = f"{env_prefix}{random_part}"
        
        # We store the first 16 chars as prefix to identify the key fast
        prefix = raw_secret[:16]
        secret_hash = pwd_context.hash(raw_secret)
        
        return raw_secret, prefix, secret_hash

    async def validate_api_key(self, raw_secret: str) -> ApiCredential:
        """Validates an API key and returns the credential if valid."""
        prefix = raw_secret[:16]
        
        stmt = select(ApiCredential).where(ApiCredential.credential_prefix == prefix)
        result = await self.db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        import logging
        logger = logging.getLogger(__name__)
        
        if not credential:
            logger.error(f"Credential not found for prefix {prefix}")
            raise HTTPException(status_code=401, detail="Invalid API credential")
            
        if not pwd_context.verify(raw_secret, credential.secret_hash):
            logger.error(f"Hash mismatch for prefix {prefix}")
            raise HTTPException(status_code=401, detail="Invalid API credential")
            
        if credential.status != "ACTIVE" or credential.revoked_at is not None:
            logger.error(f"Credential {credential.id} is not ACTIVE or is revoked")
            raise HTTPException(status_code=401, detail="API credential is revoked or suspended")
            
        if credential.expires_at and credential.expires_at < datetime.datetime.utcnow():
            logger.error(f"Credential {credential.id} expired at {credential.expires_at}")
            raise HTTPException(status_code=401, detail="API credential has expired")
            
        # Check if client is active
        stmt_client = select(ApiClient).where(ApiClient.id == credential.api_client_id)
        client = (await self.db.execute(stmt_client)).scalar_one_or_none()
        
        if not client:
            logger.error(f"Client {credential.api_client_id} not found")
            raise HTTPException(status_code=401, detail="API client is suspended or revoked")
            
        # Handle both Enum member and string representation
        client_status = client.status.value if hasattr(client.status, 'value') else client.status
        if client_status != "ACTIVE":
            logger.error(f"Client {credential.api_client_id} status is {client_status}, not ACTIVE")
            raise HTTPException(status_code=401, detail="API client is suspended or revoked")

        # Update last used
        credential.last_used_at = datetime.datetime.utcnow()
        client.last_used_at = datetime.datetime.utcnow()
        await self.db.commit()
        
        return credential

    async def revoke_credential(self, credential_id: str) -> None:
        """Revokes an active credential."""
        stmt = select(ApiCredential).where(ApiCredential.id == credential_id)
        result = await self.db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")
            
        credential.status = "REVOKED"
        credential.revoked_at = datetime.datetime.utcnow()
        await self.db.commit()
