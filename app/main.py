# app/main.py
import asyncio
from aiogram import Bot, Dispatcher
from app.config import settings
from app.handlers import user, admin
from app.services.db import init_db

async def main():
    await init_db()
    
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(user.router)
    dp.include_router(admin.router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())