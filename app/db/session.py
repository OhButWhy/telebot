from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

db_url = settings.database_url.split("?")[0]

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args={"ssl": "require"},
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False,
                                         class_=AsyncSession)
