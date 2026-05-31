import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.models import  User
from app.repositories.storage.postgres.repositories import repository

from app.transport.api.v1.schemas.user import CreateUser, OutUser


logger = logging.getLogger(__name__)


class Service:
    def __init__(self):
        self.repo = repository

    async def create_user(
        self,
        user: CreateUser,
        session: AsyncSession,
    ) -> OutUser:
        try:
            result = await self.repo.create_user(User(name=user.name), session)
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this name already exists",
            ) from exc

        await session.commit()
        return OutUser(
            id=result.id,
            name=result.name,
            created_at=result.created_at,
        )

service = Service()
