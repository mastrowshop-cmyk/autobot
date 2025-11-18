from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from .config import load_config

cfg = load_config()

engine = create_async_engine(cfg.db, echo=False)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()


async def init_db():
    from . import models  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionFactory() as session:
        yield session
