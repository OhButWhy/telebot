import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from app.config import settings
from app.bot.handlers import router as bot_router  # подключаем роутер


@asynccontextmanager
async def lifespan(app: FastAPI):
    bot = Bot(token=settings.telegram_bot_token)
    # Важно: Render даёт свой URL,но для теста локально можно оставить заглушку
    webhook_url = settings.webhook_url or f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}"
    await bot.set_webhook(f"{webhook_url}/webhook")
    app.state.bot = bot
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)
dp = Dispatcher()
dp.include_router(bot_router)  # регистрируем все хендлеры из handlers.py


@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = Update.model_validate(await request.json(),
                                   context={"bot": request.app.state.bot})
    await dp.feed_update(request.app.state.bot, update)
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}
