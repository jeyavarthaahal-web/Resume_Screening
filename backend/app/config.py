from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TalentIQ API"
    environment: str = "development"
    frontend_origins: str = ""
    supabase_url: str = Field(default="", validation_alias=AliasChoices("SUPABASE_URL", "VITE_SUPABASE_URL"))
    supabase_publishable_key: str = Field(default="", validation_alias=AliasChoices("SUPABASE_PUBLISHABLE_KEY", "VITE_SUPABASE_PUBLISHABLE_KEY"))
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
