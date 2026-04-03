"""Точка входа FastAPI-приложения."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers.payments import router as payments_router
from core.config import get_settings
from core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Здесь можно централизованно подключать long-lived ресурсы приложения.
    logger.info("app.startup")
    yield
    logger.info("app.shutdown")


app = FastAPI(title="Async Payment Processing Service", lifespan=lifespan)
app.include_router(payments_router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    """Простой healthcheck для Docker и внешних проверок."""

    return {"status": "ok"}
