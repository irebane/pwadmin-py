from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class GshopName(Base):
    __tablename__ = "gshop_names"
    item_id = Column(Integer, primary_key=True)
    item_name = Column(String(128), default="")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
