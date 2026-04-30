from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    polygon_api_key: str
    action_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("API_KEY", "ACTION_API_KEY"),
    )
    polygon_base_url: str = "https://api.massive.com"
    market_cache_ttl_seconds: int = 300

    @property
    def required_api_key(self) -> str | None:
        return self.action_api_key

    class Config:
        env_file = ".env"


settings = Settings()
