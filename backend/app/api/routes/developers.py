from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.developer import (
    ApiClientCreate, ApiClientResponse,
    ApiCredentialCreate, ApiCredentialResponse, ApiCredentialSecretResponse,
    WebhookEndpointCreate, WebhookEndpointResponse,
    WebhookDeliveryResponse, ApiRequestLogResponse
)
from app.services.developer_service import DeveloperPlatformService

router = APIRouter()

def get_developer_service(db: AsyncSession = Depends(get_db)):
    return DeveloperPlatformService(db)

# API Clients
@router.post("/clients", response_model=ApiClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    workspace_id: str,
    data: ApiClientCreate,
    current_user: User = Depends(get_current_user),
    service: DeveloperPlatformService = Depends(get_developer_service)
):
    return await service.create_client(workspace_id, data, current_user.id)

@router.get("/clients", response_model=List[ApiClientResponse])
async def get_clients(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    service: DeveloperPlatformService = Depends(get_developer_service)
):
    return await service.get_clients(workspace_id)

# API Credentials
@router.post("/credentials", response_model=ApiCredentialSecretResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    workspace_id: str,
    data: ApiCredentialCreate,
    current_user: User = Depends(get_current_user),
    service: DeveloperPlatformService = Depends(get_developer_service)
):
    cred, raw_secret = await service.create_credential(workspace_id, data, is_live=False)
    # Convert ORM to pydantic dictionary, inject secret
    base = ApiCredentialResponse.model_validate(cred)
    response = ApiCredentialSecretResponse(**base.model_dump(), secret=raw_secret)
    return response

@router.get("/credentials", response_model=List[ApiCredentialResponse])
async def get_credentials(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    service: DeveloperPlatformService = Depends(get_developer_service)
):
    return await service.get_credentials(workspace_id)

@router.post("/credentials/{credential_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_credential(
    workspace_id: str,
    credential_id: str,
    current_user: User = Depends(get_current_user),
    service: DeveloperPlatformService = Depends(get_developer_service)
):
    await service.revoke_credential(workspace_id, credential_id)

# Webhooks
@router.post("/webhooks", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    workspace_id: str,
    data: WebhookEndpointCreate,
    current_user: User = Depends(get_current_user),
    service: DeveloperPlatformService = Depends(get_developer_service)
):
    wh, raw_secret = await service.create_webhook(workspace_id, data, current_user.id)
    return wh

@router.get("/webhooks", response_model=List[WebhookEndpointResponse])
async def get_webhooks(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    service: DeveloperPlatformService = Depends(get_developer_service)
):
    return await service.get_webhooks(workspace_id)

# Request Logs
@router.get("/request-logs", response_model=List[ApiRequestLogResponse])
async def get_request_logs(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    service: DeveloperPlatformService = Depends(get_developer_service)
):
    return await service.get_request_logs(workspace_id)
