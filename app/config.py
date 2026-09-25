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

    class Config:
        env_file = ".env"


settings = Settings()
