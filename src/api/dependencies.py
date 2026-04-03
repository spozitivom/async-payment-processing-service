from application.use_cases.create_payment import CreatePaymentUseCase
from application.use_cases.get_payment import GetPaymentUseCase
from infrastructure.db.uow import SqlAlchemyUnitOfWork


def get_uow() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork()


def get_create_payment_use_case() -> CreatePaymentUseCase:
    return CreatePaymentUseCase(SqlAlchemyUnitOfWork)


def get_get_payment_use_case() -> GetPaymentUseCase:
    return GetPaymentUseCase(SqlAlchemyUnitOfWork)
