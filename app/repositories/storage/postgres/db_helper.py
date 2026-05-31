from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Any
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings
import logging


logger = logging.getLogger(__name__)


class DatabaseHelper:
    def __init__(self, url: str, echo: bool = False, **engine_kwargs: Any):
        self.engine = create_async_engine(url=url, echo=echo, **engine_kwargs)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def transaction(self):
        async with self.session_factory() as session:
            try:
                yield session
                if session.in_transaction():
                    await session.commit()
            except Exception as e:
                if session.in_transaction():
                    await session.rollback()
                logger.error("Failed transaction error: %s", e)
                raise e

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.transaction() as session:
            yield session


db_helper = DatabaseHelper(url=settings.database_url)
