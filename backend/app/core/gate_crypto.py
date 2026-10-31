import hmac
import hashlib
import json
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from app.core.config import settings
from app.schemas.execution_context import SignedGateDecision

class GateCrypto:
    @staticmethod
    def sign_payload(payload: Dict[str, Any]) -> str:
        if not settings.ENCRYPTION_KEY or not settings.ENCRYPTION_KEY.strip():
            raise ValueError("Cryptographic operation failed: ENCRYPTION_KEY is not configured")
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            settings.ENCRYPTION_KEY.encode("utf-8"),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return signature

    @staticmethod
    def generate_token(decision: SignedGateDecision) -> str:
        payload = decision.model_dump(mode='json')
        # Remove empty or none values for consistent signing if desired, but model_dump(mode='json') is consistent enough.
        # We will sort keys during signing to ensure consistent ordering.
        signature = GateCrypto.sign_payload(payload)
        
        # Structure the token as base64(payload).signature
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
        return f"{payload_b64}.{signature}"

    @staticmethod
    def verify_token(token: str) -> SignedGateDecision:
        if not settings.ENCRYPTION_KEY or not settings.ENCRYPTION_KEY.strip():
            raise ValueError("Cryptographic verification failed: ENCRYPTION_KEY is not configured")
        try:
            payload_b64, signature = token.rsplit(".", 1)
        except ValueError:
            raise ValueError("Invalid token format")
            
        try:
            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            payload = json.loads(payload_json)
        except Exception:
            raise ValueError("Invalid token payload")
            
        expected_signature = GateCrypto.sign_payload(payload)
        
        if not hmac.compare_digest(expected_signature, signature):
            raise ValueError("Invalid signature")
            
        decision = SignedGateDecision(**payload)
        
        expires_at = decision.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if expires_at < datetime.now(timezone.utc):
            raise ValueError("Token expired")
            
        issued_at = decision.issued_at
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)
            
        if issued_at > datetime.now(timezone.utc) + timedelta(minutes=1):
            raise ValueError("Token issued in the future")
            
        return decision
