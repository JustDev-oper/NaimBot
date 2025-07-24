from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = []
    WORKERS_CHAT_ID: Optional[int] = None
    WORKERS_CHAT_LINK: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings() 