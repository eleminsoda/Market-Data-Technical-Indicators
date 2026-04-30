from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    polygon_api_key: str
    action_api_key: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
