import json
import hashlib
from typing import Any
from datetime import datetime, timezone
import uuid

def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def canonical_json_serialize(data: Any) -> bytes:
    """
    Serializes a Python object to a canonical JSON byte string.
    Ensures keys are sorted, spaces are minimized, and UTF-8 encoding is used.
    """
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
        default=_json_default
    ).encode('utf-8')

def compute_hash(data: Any, previous_hash: str = None) -> str:
    """
    Computes a SHA-256 hash for the given data (after canonicalization) 
    combined with the previous hash to form a tamper-evident chain.
    """
    hasher = hashlib.sha256()
    
    if previous_hash:
        hasher.update(previous_hash.encode('utf-8'))
        
    hasher.update(canonical_json_serialize(data))
    return hasher.hexdigest()
