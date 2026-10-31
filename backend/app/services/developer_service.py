import uuid
import datetime
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.developer import ApiClient, ApiCredential, WebhookEndpoint, ApiRequestLog
from app.schemas.developer import ApiClientCreate, ApiCredentialCreate, WebhookEndpointCreate
from app.services.developer_auth import DeveloperAuthService

class DeveloperPlatformService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.auth_svc = DeveloperAuthService(db)

    # API Clients
    async def create_client(self, workspace_id: str, data: ApiClientCreate, user_id: str) -> ApiClient:
        client = ApiClient(
            workspace_id=workspace_id,
            name=data.name,
            description=data.description,
            created_by=user_id
        )
        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        return client

    async def get_clients(self, workspace_id: str) -> List[ApiClient]:
        stmt = select(ApiClient).where(ApiClient.workspace_id == workspace_id)
        return (await self.db.execute(stmt)).scalars().all()

    # API Credentials
    async def create_credential(self, workspace_id: str, data: ApiCredentialCreate, is_live: bool = False) -> Tuple[ApiCredential, str]:
        # Validate client belongs to workspace
        stmt = select(ApiClient).where(ApiClient.id == data.api_client_id, ApiClient.workspace_id == workspace_id)
        client = (await self.db.execute(stmt)).scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="API Client not found")

        raw_secret, prefix, secret_hash = self.auth_svc.generate_api_key(is_live=is_live)
        
        cred = ApiCredential(
            api_client_id=client.id,
            workspace_id=workspace_id,
            name=data.name,
            credential_prefix=prefix,
            secret_hash=secret_hash,
            scopes=data.scopes
        )
        
        self.db.add(cred)
        await self.db.commit()
        await self.db.refresh(cred)
        
        return cred, raw_secret

    async def get_credentials(self, workspace_id: str, client_id: Optional[str] = None) -> List[ApiCredential]:
        stmt = select(ApiCredential).where(ApiCredential.workspace_id == workspace_id)
        if client_id:
            stmt = stmt.where(ApiCredential.api_client_id == client_id)
        return (await self.db.execute(stmt)).scalars().all()

    async def revoke_credential(self, workspace_id: str, credential_id: str) -> None:
        stmt = select(ApiCredential).where(ApiCredential.id == credential_id, ApiCredential.workspace_id == workspace_id)
        cred = (await self.db.execute(stmt)).scalar_one_or_none()
        if not cred:
            raise HTTPException(status_code=404, detail="Credential not found")
        await self.auth_svc.revoke_credential(cred.id)

    # Webhooks
    async def create_webhook(self, workspace_id: str, data: WebhookEndpointCreate, user_id: str) -> Tuple[WebhookEndpoint, str]:
        raw_secret, _, secret_hash = self.auth_svc.generate_api_key(is_live=True)
        
        wh = WebhookEndpoint(
            workspace_id=workspace_id,
            url=data.url,
            description=data.description,
            subscribed_events=data.subscribed_events,
            secret_hash=secret_hash,
            created_by=user_id
        )
        self.db.add(wh)
        await self.db.commit()
        await self.db.refresh(wh)
        return wh, raw_secret

    async def get_webhooks(self, workspace_id: str) -> List[WebhookEndpoint]:
        stmt = select(WebhookEndpoint).where(WebhookEndpoint.workspace_id == workspace_id)
        return (await self.db.execute(stmt)).scalars().all()

    # Request Logs
    async def get_request_logs(self, workspace_id: str, limit: int = 100) -> List[ApiRequestLog]:
        stmt = select(ApiRequestLog).where(ApiRequestLog.workspace_id == workspace_id).order_by(ApiRequestLog.occurred_at.desc()).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()

    async def log_request(self, workspace_id: str, method: str, route: str, status_code: int, latency_ms: int,
                          client_id: Optional[str] = None, credential_id: Optional[str] = None, correlation_id: Optional[str] = None):
        log_entry = ApiRequestLog(
            workspace_id=workspace_id,
            api_client_id=client_id,
            credential_id=credential_id,
            method=method,
            route=route,
            status_code=status_code,
            latency_ms=latency_ms,
            correlation_id=correlation_id
        )
        self.db.add(log_entry)
        await self.db.commit()
