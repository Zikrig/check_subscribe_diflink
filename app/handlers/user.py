# app/handlers/user.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select 

from app.keyboards import subscription_keyboard
from app.services.db import SessionLocal, Promotion, Channel 


router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    async with SessionLocal() as session:
        promo = await session.get(Promotion, 1)
        if promo and promo.welcome_photo:
            await message.answer_photo(
                photo=promo.welcome_photo,
                caption=promo.welcome_text,
                reply_markup=await subscription_keyboard()
            )
        else:
            await message.answer(
                text=promo.welcome_text if promo else "Добро пожаловать!",
                reply_markup=await subscription_keyboard()
            )

@router.callback_query(F.data == "check_subs")
async def check_subs(callback: CallbackQuery, bot: Bot):
    async with SessionLocal() as session:
        # Получаем все активные каналы
        channels = await session.execute(
            select(Channel).where(Channel.is_active == True)
        )
        channels = channels.scalars().all()
        
        # Проверяем подписку на каждый канал
        not_subbed = []
        for channel in channels:
            try:
                # Проверяем подписку пользователя
                chat_member = await bot.get_chat_member(
                    chat_id=channel.chat_id,
                    user_id=callback.from_user.id
                )
                if chat_member.status not in ['member', 'administrator', 'creator']:
                    not_subbed.append(channel)
            except Exception:
                not_subbed.append(channel)
        
        if not_subbed:
            # Если не подписан на какие-то каналы
            message_text = "Вы не подписались на следующие каналы:\n"
            for channel in not_subbed:
                message_text += f"- {channel.name}\n"
            await callback.answer(message_text, show_alert=True)
        else:
            # Если подписан на все каналы
            promo = await session.get(Promotion, 1)
            if promo:
                promo.click_count += 1
                await session.commit()

                await callback.message.answer(
                    f"Спасибо! Ваша ссылка: {promo.action_url}\n\n"
                    # f"Уникальный ID для отслеживания: {callback.from_user.id}"
                )
                
                await callback.answer()