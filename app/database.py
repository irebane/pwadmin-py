from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

DATABASE_URL = (
    f"mysql+aiomysql://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}/{settings.db_name}?charset=utf8mb4"
)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
