from sqlalchemy import Column, String, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    
    language = Column(String, default="en", nullable=False)
    timezone = Column(String, default="UTC", nullable=False)
    date_format = Column(String, default="YYYY-MM-DD", nullable=False)
    
    notification_preferences = Column(JSON, default=dict, nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="preferences")
