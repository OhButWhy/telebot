import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

from app.db.models import Base  # noqa: E402

config = context.config

# Подставляем URL из переменной окружения
db_url = os.environ.get("DATABASE_URL", "")
if not db_url:
    # fallback: читаем из .env вручную
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)
    db_url = os.environ.get("DATABASE_URL", "")
assert db_url, "DATABASE_URL не найдена! Проверь переменную окружения или .env"

# Миграции выполняются синхронным движком:
# asyncpg драйвер для этого не годится, убираем +asyncpg
sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection,
                          target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
