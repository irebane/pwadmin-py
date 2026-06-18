from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    ID = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    passwd = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False)
    idnumber = Column(String(32))
    truename = Column(String(64))
    sex = Column(Integer, default=0)
    birthday = Column(String(16))
    regtime = Column(DateTime, server_default=func.now())
    webpoint = Column(Integer, default=0)


class Point(Base):
    __tablename__ = "point"
    uid = Column(Integer, primary_key=True)
    webpoint = Column(Integer, default=0)
    loginpoint = Column(Integer, default=0)
    zoneid = Column(Integer, nullable=True)


class Auth(Base):
    __tablename__ = "auth"
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(String(64))


class Forbid(Base):
    __tablename__ = "forbid"
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(String(64))
    type = Column(Integer)
    endtime = Column(Integer)
    starttime = Column(Integer)
    reason = Column(Text)


class IpLimit(Base):
    __tablename__ = "iplimit"
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer)
    ip = Column(String(64))
