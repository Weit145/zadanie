import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.models import User


class SQLAlchemyRepository:
    async def create_user(self, user: User, session: AsyncSession) -> User:
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user

    async def get_user_by_id(
        self,
        user_id: uuid.UUID,
        session: AsyncSession,
    ) -> User | None:
        return await session.get(User, user_id)


repository = SQLAlchemyRepository()
