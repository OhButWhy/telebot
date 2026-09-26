import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from app.config import settings
from app.bot.handlers import router as bot_router

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot = Bot(token=settings.telegram_bot_token)

    # Получаем адрес. RENDER_EXTERNAL_URL есть всегда у веб-сервисов
    webhook_base = os.getenv("RENDER_EXTERNAL_URL") or settings.webhook_url

    if webhook_base:
        webhook_url = f"{webhook_base}/webhook"
        try:
            logger.info(f"Trying to set webhook to: {webhook_url}")
            result = await bot.set_webhook(webhook_url)
            logger.info(f"Webhook set successfully: {result}")
        except Exception as e:
            # ЭТО САМОЕ ВАЖНОЕ: если тут ошибка — она появится в логах красным!
            logger.error(f"Failed to set webhook: {e}", exc_info=True)
            # Не прерываем старт приложения, но в логах будет причина
    else:
        logger.warning("Cannot set webhook: RENDER_EXTERNAL_URL is missing")

    app.state.bot = bot
    yield

app = FastAPI(lifespan=lifespan)
dp = Dispatcher()
dp.include_router(bot_router)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = Update.model_validate(await request.json(),
                                   context={"bot": request.app.state.bot})
    await dp.feed_update(request.app.state.bot, update)
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}
