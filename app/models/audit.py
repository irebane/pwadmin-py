from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    admin_user = Column(String(64))
    action = Column(String(64))
    params = Column(JSON)
    result = Column(Text)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ip = Column(String(64), index=True)
    username = Column(String(64))
    attempted_at = Column(DateTime, server_default=func.now())
    success = Column(Integer, default=0)
