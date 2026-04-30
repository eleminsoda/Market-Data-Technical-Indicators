from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    polygon_api_key: str
    action_api_key: str | None = None
    polygon_base_url: str = "https://api.massive.com"
    market_cache_ttl_seconds: int = 1800

    class Config:
        env_file = ".env"


settings = Settings()
