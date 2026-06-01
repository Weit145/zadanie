import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.storage.postgres.db_helper import db_helper
from app.transport.api.v1.schemas.payment_method import (
    CreatePaymentMethod,
    OutPaymentMethod,
    UpdatePaymentMethod,
)
from app.usecase.service import service


router = APIRouter(tags=["Payment methods"])


@router.post(
    "/users/{user_id}/payment-methods",
    status_code=status.HTTP_201_CREATED,
    response_model=OutPaymentMethod,
)
async def create_payment_method(
    user_id: uuid.UUID,
    payment_method: Annotated[CreatePaymentMethod, Body(title="The payment method data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutPaymentMethod:
    return await service.create_payment_method(user_id, payment_method, session)


@router.get("/users/{user_id}/payment-methods", response_model=list[OutPaymentMethod])
async def list_payment_methods(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> list[OutPaymentMethod]:
    return await service.list_payment_methods(user_id, session)


@router.get("/payment-methods/{payment_method_id}", response_model=OutPaymentMethod)
async def get_payment_method(
    payment_method_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutPaymentMethod:
    return await service.get_payment_method(payment_method_id, session)


@router.patch("/payment-methods/{payment_method_id}", response_model=OutPaymentMethod)
async def update_payment_method(
    payment_method_id: uuid.UUID,
    payment_method: Annotated[UpdatePaymentMethod, Body(title="The payment method data")],
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> OutPaymentMethod:
    return await service.update_payment_method(payment_method_id, payment_method, session)


@router.delete("/payment-methods/{payment_method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    payment_method_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(db_helper.get_session)],
) -> None:
    await service.delete_payment_method(payment_method_id, session)
