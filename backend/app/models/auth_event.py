from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class AuthEvent(Base):
    __tablename__ = 'auth_events'

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=True) # nullable for failed logins with unknown email
    event_type = Column(String, nullable=False) # e.g. LOGIN_FAILED, PASSWORD_RESET
    ip_metadata = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User')
