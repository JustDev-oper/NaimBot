from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = []
    WORKERS_CHAT_ID: Optional[int] = None
    WORKERS_CHAT_LINK: Optional[str] = None

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASS: str = "password"
    DB_NAME: str = "naimbot"

    BOT_USERNAME: Optional[str] = None  # username бота без @

    class Config:
        env_file = ".env"

settings = Settings() 