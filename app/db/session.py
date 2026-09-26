from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, \
                                    async_sessionmaker
from app.config import settings

# Отрезаем всё после ? чтобы asyncpg не ругался
db_url = settings.async_db_url.split("?")[0]

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args={"ssl": "require"},  # Render требует SSL
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False,
                                         class_=AsyncSession)
