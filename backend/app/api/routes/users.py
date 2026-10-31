from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.db.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.user_service import get_or_create_user_preferences, update_user_preferences, update_user_profile

router = APIRouter()

@router.get("/me")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "status": current_user.status,
            "email_verified_at": current_user.email_verified_at,
        }
    }

@router.patch("/me")
async def patch_my_profile(update_data: Dict[str, Any], current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    updated_user = await update_user_profile(db, current_user, update_data)
    return {
        "message": "Profile updated successfully",
        "user": {
            "id": updated_user.id,
            "full_name": updated_user.full_name,
            "avatar_url": updated_user.avatar_url,
        }
    }

@router.get("/me/preferences")
async def get_my_preferences(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    prefs = await get_or_create_user_preferences(db, current_user.id)
    return {
        "preferences": {
            "language": prefs.language,
            "timezone": prefs.timezone,
            "date_format": prefs.date_format,
            "notification_preferences": prefs.notification_preferences,
        }
    }

@router.patch("/me/preferences")
async def patch_my_preferences(update_data: Dict[str, Any], current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if "notification_preferences" in update_data:
        notifs = update_data["notification_preferences"]
        if "txThreshold" in notifs:
            try:
                tx_val = float(notifs["txThreshold"])
                if tx_val < 0:
                    raise ValueError()
                notifs["txThreshold"] = tx_val
            except (ValueError, TypeError):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Transaction Exceeds threshold. Must be a positive number.")
        if "dailyThreshold" in notifs:
            try:
                daily_val = float(notifs["dailyThreshold"])
                if daily_val < 0:
                    raise ValueError()
                notifs["dailyThreshold"] = daily_val
            except (ValueError, TypeError):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Daily Agent Exposure threshold. Must be a positive number.")

    updated_prefs = await update_user_preferences(db, current_user.id, update_data)
    return {
        "message": "Preferences updated successfully",
        "preferences": {
            "language": updated_prefs.language,
            "timezone": updated_prefs.timezone,
            "date_format": updated_prefs.date_format,
            "notification_preferences": updated_prefs.notification_preferences,
        }
    }
