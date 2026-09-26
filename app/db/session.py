from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import settings

db_url = make_url(settings.async_db_url)
sslmode = db_url.query.get("sslmode")
if sslmode:
    db_url = db_url.update_query_dict({}, append=False)

connect_args = {"ssl": True} if sslmode == "require" else {}

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False,
                                         class_=AsyncSession)
