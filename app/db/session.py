from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, \
                                    async_sessionmaker
from app.config import settings


engine = create_async_engine(settings.async_db_url, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False,
                                         class_=AsyncSession)


async def get_session():
    async with async_session_maker() as session:
        yield session
