from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger
from app.database import Base


class User(Base):
    __tablename__ = "users"
    ID = Column(Integer, primary_key=True)
    name = Column(String(32), unique=True, nullable=False)
    passwd = Column(String(64), nullable=False)
    email = Column(String(64), nullable=False)
    idnumber = Column(String(32))
    truename = Column(String(32))
    gender = Column(Integer, default=0)
    birthday = Column(DateTime)
    creatime = Column(DateTime)
    passwd2 = Column(String(64))
    Prompt = Column(String(32), default="")
    answer = Column(String(32), default="")
    mobilenumber = Column(String(32))
    qq = Column(String(32))


class Point(Base):
    """Login session / zone tracking table — not a points balance."""
    __tablename__ = "point"
    uid = Column(Integer, primary_key=True)
    aid = Column(Integer, primary_key=True)
    time = Column(Integer, default=0)
    zoneid = Column(Integer)
    zonelocalid = Column(Integer)
    accountstart = Column(DateTime)
    lastlogin = Column(DateTime)
    enddate = Column(DateTime)


class Auth(Base):
    __tablename__ = "auth"
    userid = Column(Integer, primary_key=True)
    zoneid = Column(Integer, primary_key=True)
    rid = Column(Integer, primary_key=True)


class Forbid(Base):
    __tablename__ = "forbid"
    userid = Column(Integer, primary_key=True)
    type = Column(Integer, primary_key=True)
    ctime = Column(DateTime)
    forbid_time = Column(Integer, default=0)
    reason = Column(Text)
    gmroleid = Column(Integer)


class IpLimit(Base):
    __tablename__ = "iplimit"
    id = Column(Integer, primary_key=True, autoincrement=True)
    userid = Column(Integer)
    ip = Column(String(64))
