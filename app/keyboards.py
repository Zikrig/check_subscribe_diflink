# app/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot
from app.services.db import SessionLocal, Channel, select, insert

async def subscription_keyboard():
    buttons = []
    async with SessionLocal() as session:
        channels = await session.execute(
            select(Channel).where(Channel.is_active == True)
        )
        channels = channels.scalars().all()
        
        for channel in channels:
            button = InlineKeyboardButton(
                text=channel.name,
                url=channel.url
            )
            buttons.append([button])

    check_button = InlineKeyboardButton(text="Я подписался", callback_data="check_subs")
    buttons.append([check_button])

    return InlineKeyboardMarkup(inline_keyboard=buttons)