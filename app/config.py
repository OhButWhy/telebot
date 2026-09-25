from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str

    database_url: str

    aws_access_key_id: str
    aws_secret_access_key: str
    s3_endpoint_url: str
    s3_bucket_name: str

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    @property
    def webhook_url(self) -> str | None:
        return self._env.get("WEBHOOK_URL")

    class Config:
        env_file = ".env"


settings = Settings()
