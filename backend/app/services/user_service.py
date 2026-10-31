import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.models.user import User
from app.models.user_preferences import UserPreferences

async def get_or_create_user_preferences(db: AsyncSession, user_id: str) -> UserPreferences:
    result = await db.execute(select(UserPreferences).where(UserPreferences.user_id == user_id))
    prefs = result.scalars().first()
    
    if not prefs:
        prefs = UserPreferences(
            id=str(uuid.uuid4()),
            user_id=user_id,
            notification_preferences={}
        )
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
        
    return prefs

async def update_user_preferences(db: AsyncSession, user_id: str, update_data: dict) -> UserPreferences:
    prefs = await get_or_create_user_preferences(db, user_id)
    
    for key, value in update_data.items():
        if hasattr(prefs, key) and key not in ["id", "user_id", "updated_at"]:
            setattr(prefs, key, value)
            
    await db.commit()
    await db.refresh(prefs)
    return prefs

async def update_user_profile(db: AsyncSession, user: User, update_data: dict) -> User:
    for key, value in update_data.items():
        if hasattr(user, key) and key in ["full_name", "avatar_url"]:
            setattr(user, key, value)
            
    await db.commit()
    await db.refresh(user)
    return user
