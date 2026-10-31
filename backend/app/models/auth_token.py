from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
import enum
from app.db.database import Base

class AuthTokenType(str, enum.Enum):
    VERIFICATION = 'VERIFICATION'
    RESET = 'RESET'

class AuthToken(Base):
    __tablename__ = 'auth_tokens'

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    type = Column(Enum(AuthTokenType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship('User')
