from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    API_PREFIX: str = "/api"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["*"]
    DATABASE_URL: str = "sqlite:///./database.db"
    ORIGIN_API_KEY: str
    SECRET_KEY: str
    OPENAI_API_KEY: Optional[str] = None  

    @field_validator("ALLOWED_ORIGINS",mode="before")
    def parse_allowed_origins(cls, v: str) -> List[str]:
        if isinstance(v, str):
            return v.split(",")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
settings = Settings()