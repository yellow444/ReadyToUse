"""Global settings (English comments as requested)"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENWEATHER_API_KEY: str = ""
    KUDAGO_API_BASE: str = "https://kudago.com/public-api/v1.4"
    RETRY_ATTEMPTS: int = 5
    RETRY_WAIT: int = 2

    class Config:
        env_file = ".env"


settings = Settings()
