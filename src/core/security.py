"""Проверка статического API-ключа для всех HTTP endpoint."""

from fastapi import Header, HTTPException, status

from core.config import get_settings


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    # Явно возвращаем 401 и для отсутствующего, и для неверного ключа,
    # чтобы контракт авторизации не зависел от валидации FastAPI по required header.
    settings = get_settings()
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
