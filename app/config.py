# app/config.py
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMINS = [int(a.strip()) for a in os.getenv("ADMINS", "").split(",") if a]

    SQLITE_PATH = Path(os.getenv("SQLITE_PATH", "data/bot.db"))
    DB_URL = f"sqlite+aiosqlite:///{SQLITE_PATH.as_posix()}"

settings = Settings()