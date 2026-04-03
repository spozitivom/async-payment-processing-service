"""HTTP-роуты для создания и чтения платежей."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from api.dependencies import get_create_payment_use_case, get_get_payment_use_case
from api.schemas.payments import CreatePaymentRequest, PaymentAcceptedResponse, PaymentResponse
from application.dto.payments import CreatePaymentCommand
from application.use_cases.create_payment import CreatePaymentUseCase
from application.use_cases.get_payment import GetPaymentUseCase
from core.exceptions import PaymentNotFoundError
from core.security import verify_api_key

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=PaymentAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
    payload: CreatePaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    use_case: CreatePaymentUseCase = Depends(get_create_payment_use_case),
) -> PaymentAcceptedResponse:
    """Принимает платеж и делегирует бизнес-логику use case без ORM-деталей в роутере."""

    result = await use_case.execute(
        CreatePaymentCommand(
            amount=payload.amount,
            currency=payload.currency,
            description=payload.description,
            metadata=payload.metadata,
            webhook_url=payload.webhook_url,
            idempotency_key=idempotency_key,
        )
    )
    return PaymentAcceptedResponse(**result.model_dump())


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    use_case: GetPaymentUseCase = Depends(get_get_payment_use_case),
) -> PaymentResponse:
    """Возвращает текущее состояние платежа по его идентификатору."""

    try:
        result = await use_case.execute(payment_id)
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PaymentResponse(**result.model_dump())
