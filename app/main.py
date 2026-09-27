import os
import logging
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Request, status
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from sqlalchemy import text

from app.config import settings
from app.bot.routers import router as bot_router
from app.db.session import async_session_maker, engine

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot = Bot(token=settings.telegram_bot_token)

    # Получаем адрес. RENDER_EXTERNAL_URL есть всегда у веб-сервисов
    webhook_base = os.getenv("RENDER_EXTERNAL_URL") or settings.webhook_url

    if webhook_base:
        webhook_url = f"{webhook_base.rstrip('/')}/webhook"
        try:
            logger.info(f"Trying to set webhook to: {webhook_url}")
            result = await bot.set_webhook(
                webhook_url,
                secret_token=settings.webhook_secret or None,
            )
            logger.info(f"Webhook set successfully: {result}")
        except Exception as e:
            # ЭТО САМОЕ ВАЖНОЕ: если тут ошибка — она появится в логах красным!
            logger.error(f"Failed to set webhook: {e}", exc_info=True)
            # Не прерываем старт приложения, но в логах будет причина
    else:
        logger.warning("Cannot set webhook: RENDER_EXTERNAL_URL is missing")

    app.state.bot = bot
    try:
        yield
    finally:
        await bot.session.close()
        await engine.dispose()

app = FastAPI(lifespan=lifespan)
dp = Dispatcher()
dp.include_router(bot_router)


@app.post("/webhook")
async def telegram_webhook(
    request: Request,
    telegram_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
):
    if settings.webhook_secret and not secrets.compare_digest(
        telegram_secret_token or "", settings.webhook_secret
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    update = Update.model_validate(await request.json(),
                                   context={"bot": request.app.state.bot})
    await dp.feed_update(request.app.state.bot, update)
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
async def readiness():
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    return {"status": "ready"}
