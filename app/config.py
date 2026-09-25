from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    database_url: str
    webhook_url: str = ""

    @property
    def async_db_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    class Config:
        env_file = ".env"


settings = Settings()
