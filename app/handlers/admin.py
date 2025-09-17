# app/handlers/admin.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ContentType
from urllib.parse import urlparse
import re

from app.services.db import SessionLocal, Promotion, Channel, insert, select
from app.config import settings


router = Router()

class EditPromotion(StatesGroup):
    editing_text = State()
    editing_photo = State()
    editing_url = State()

class EditChannel(StatesGroup):
    editing_name = State()
    editing_url = State()
    editing_chat_id = State()
    selecting_channel = State()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in settings.ADMINS:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Редактировать приветствие", callback_data="edit_welcome")],
        [InlineKeyboardButton(text="Редактировать ссылку акции", callback_data="edit_action_url")],
        [InlineKeyboardButton(text="Управление каналами", callback_data="manage_channels")],
        [InlineKeyboardButton(text="Статистика", callback_data="show_stats")]
    ])
    
    await message.answer("Панель администратора:", reply_markup=keyboard)

@router.callback_query(F.data == "edit_welcome")
async def edit_welcome_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Текст", callback_data="edit_welcome_text")],
        [InlineKeyboardButton(text="Изображение", callback_data="edit_welcome_photo")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_back")]
    ])
    await callback.message.edit_text("Что хотите изменить?", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "edit_welcome_photo")
async def edit_welcome_photo(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте новое изображение для приветствия:")
    await state.set_state(EditPromotion.editing_photo)
    await callback.answer()
    
@router.message(EditPromotion.editing_photo, F.content_type == ContentType.PHOTO)
async def save_welcome_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    async with SessionLocal() as session:
        promo = await session.get(Promotion, 1)
        if not promo:
            promo = Promotion(id=1)
            session.add(promo)
        promo.welcome_photo = photo_id
        await session.commit()
    await message.answer("Изображение приветствия обновлено!")
    await state.clear()

# Добавим обработчик для неверного типа сообщения
@router.message(EditPromotion.editing_photo)
async def invalid_photo_message(message: Message):
    await message.answer("Пожалуйста, отправьте изображение.")


@router.callback_query(F.data == "edit_welcome_text")
async def edit_welcome_text(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте новый текст приветствия:")
    await state.set_state(EditPromotion.editing_text)
    await callback.answer()
    
    
# Добавим кнопку сброса счетчика в статистику
@router.callback_query(F.data == "show_stats")
async def show_stats(callback: CallbackQuery):
    async with SessionLocal() as session:
        promo = await session.get(Promotion, 1)
        if promo:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Сбросить счетчик", callback_data="reset_counter")]
            ])
            await callback.message.answer(
                f"Уникальных переходов: {promo.click_count}",
                reply_markup=keyboard
            )
    await callback.answer()

# Добавим обработчик сброса счетчика
@router.callback_query(F.data == "reset_counter")
async def reset_counter(callback: CallbackQuery):
    async with SessionLocal() as session:
        promo = await session.get(Promotion, 1)
        if promo:
            promo.click_count = 0
            await session.commit()
            await callback.answer("Счетчик обнулен!")
        else:
            await callback.answer("Ошибка: запись не найдена")
            
            
@router.message(EditPromotion.editing_text)
async def save_welcome_text(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        promo = await session.get(Promotion, 1)
        if not promo:
            promo = Promotion(id=1)
            session.add(promo)
        promo.welcome_text = message.text
        await session.commit()
    await message.answer("Текст приветствия обновлен!")
    await state.clear()

@router.callback_query(F.data == "edit_action_url")
async def edit_action_url_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте новую ссылку для акции:")
    await state.set_state(EditPromotion.editing_url)
    await callback.answer()

@router.message(EditPromotion.editing_url)
async def save_action_url(message: Message, state: FSMContext):
    # Проверяем, что введенный текст является валидным URL
    url = message.text.strip()
    
    # Простая проверка URL с помощью регулярного выражения
    url_pattern = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'(([A-Z0-9-]+\.)+[A-Z]{2,})'  # domain
        r'(:[0-9]+)?'  # port
        r'(/.*)?$',  # path
        re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        await message.answer("Ошибка: введите корректный URL (например, https://example.com)")
        return
    
    # Более строгая проверка с помощью urlparse
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            await message.answer("Ошибка: введите корректный URL с указанием протокола (http:// или https://)")
            return
    except:
        await message.answer("Ошибка: введите корректный URL")
        return
    
    async with SessionLocal() as session:
        promo = await session.get(Promotion, 1)
        if not promo:
            promo = Promotion(id=1)
            session.add(promo)
        promo.action_url = url
        await session.commit()
    await message.answer("Ссылка акции обновлена!")
    await state.clear()
    
@router.callback_query(F.data == "manage_channels")
async def manage_channels(callback: CallbackQuery):
    async with SessionLocal() as session:
        channels = await session.execute(select(Channel))
        channels = channels.scalars().all()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for channel in channels:
            status = "✅" if channel.is_active else "❌"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {channel.name} - {channel.url}",
                    callback_data=f"edit_channel_{channel.id}"
                )
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="Добавить канал", callback_data="add_channel")
        ])
        
        await callback.message.edit_text("Управление каналами:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("edit_channel_"))
async def edit_channel(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split("_")[2])
    await state.update_data(channel_id=channel_id)
    
    async with SessionLocal() as session:
        channel = await session.get(Channel, channel_id)
        status = "✅" if channel.is_active else "❌"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Изменить имя", callback_data="change_name")],
        [InlineKeyboardButton(text="Изменить ссылку", callback_data="change_url")],
        [InlineKeyboardButton(text="Изменить chat_id", callback_data="change_chat_id")],
        [InlineKeyboardButton(text=f"{'Выключить' if channel.is_active else 'Включить'} канал", 
                             callback_data="toggle_channel")],
        [InlineKeyboardButton(text="Назад", callback_data="manage_channels")]
    ])
    
    await callback.message.edit_text(
        f"Канал: {channel.name}\n"
        f"URL: {channel.url}\n"
        f"Chat ID: {channel.chat_id}\n"
        f"Статус: {status}",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "toggle_channel")
async def toggle_channel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    
    async with SessionLocal() as session:
        channel = await session.get(Channel, channel_id)
        channel.is_active = not channel.is_active
        await session.commit()
        
        status = "✅" if channel.is_active else "❌"
        await callback.answer(f"Канал {'включен' if channel.is_active else 'выключен'}")
        
        # Обновляем сообщение
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Изменить имя", callback_data="change_name")],
            [InlineKeyboardButton(text="Изменить ссылку", callback_data="change_url")],
            [InlineKeyboardButton(text="Изменить chat_id", callback_data="change_chat_id")],
            [InlineKeyboardButton(text=f"{'Выключить' if channel.is_active else 'Включить'} канал", 
                                 callback_data="toggle_channel")],
            [InlineKeyboardButton(text="Назад", callback_data="manage_channels")]
        ])
        
        await callback.message.edit_text(
            f"Канал: {channel.name}\n"
            f"URL: {channel.url}\n"
            f"Chat ID: {channel.chat_id}\n"
            f"Статус: {status}",
            reply_markup=keyboard
        )
        
@router.callback_query(F.data == "change_name")
async def change_channel_name(callback: CallbackQuery, state: FSMContext):
    
    # Получаем channel_id из состояния
    data = await state.get_data()
    channel_id = data.get("channel_id")
    
    if not channel_id:
        await callback.answer("Ошибка: не найден ID канала")
        return
        
    await callback.message.answer("Введите новое имя для канала:")
    await state.set_state(EditChannel.editing_name)
    await callback.answer()

@router.callback_query(F.data == "change_url")
async def change_channel_url(callback: CallbackQuery, state: FSMContext):
    # Получаем channel_id из состояния
    data = await state.get_data()
    channel_id = data.get("channel_id")
    
    if not channel_id:
        await callback.answer("Ошибка: не найден ID канала")
        return
        
    await callback.message.answer("Введите новую ссылку для канала:")
    await state.set_state(EditChannel.editing_url)
    await callback.answer()

@router.message(EditChannel.editing_name)
async def save_channel_name(message: Message, state: FSMContext):
    # Получаем channel_id из состояния
    data = await state.get_data()
    channel_id = data.get("channel_id")
    
    if not channel_id:
        await message.answer("Ошибка: не найден ID канала")
        await state.clear()
        return
    
    async with SessionLocal() as session:
        channel = await session.get(Channel, channel_id)
        if channel:
            channel.name = message.text
            await session.commit()
            await message.answer("Имя канала обновлено!")
        else:
            await message.answer("Ошибка: канал не найден")
    
    await state.clear()

@router.message(EditChannel.editing_url)
async def save_channel_url(message: Message, state: FSMContext):
    # Получаем channel_id из состояния
    data = await state.get_data()
    channel_id = data.get("channel_id")
    
    if not channel_id:
        await message.answer("Ошибка: не найден ID канала")
        await state.clear()
        return
    
    # Проверяем, что введенный текст является валидным URL
    url = message.text.strip()
    
    # Простая проверка URL с помощью регулярного выражения
    url_pattern = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'(([A-Z0-9-]+\.)+[A-Z]{2,})'  # domain
        r'(:[0-9]+)?'  # port
        r'(/.*)?$',  # path
        re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        await message.answer("Ошибка: введите корректный URL (например, https://example.com)")
        return
    
    # Более строгая проверка с помощью urlparse
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            await message.answer("Ошибка: введите корректный URL с указанием протокола (http:// или https://)")
            return
    except:
        await message.answer("Ошибка: введите корректный URL")
        return
    
    async with SessionLocal() as session:
        channel = await session.get(Channel, channel_id)
        if channel:
            channel.url = url
            await session.commit()
            await message.answer("Ссылка канала обновлена!")
        else:
            await message.answer("Ошибка: канал не найден")
    
    await state.clear()
    
    
@router.callback_query(F.data == "show_stats")
async def show_stats(callback: CallbackQuery):
    async with SessionLocal() as session:
        promo = await session.get(Promotion, 1)
        if promo:
            await callback.message.answer(f"Уникальных переходов: {promo.click_count}")
    await callback.answer()
    
@router.callback_query(F.data == "change_chat_id")
async def change_channel_chat_id(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    
    if not channel_id:
        await callback.answer("Ошибка: не найден ID канала")
        return
        
    await callback.message.answer("Введите новый chat_id для канала (например, @channel или -100123456789):")
    await state.set_state(EditChannel.editing_chat_id)
    await callback.answer()

@router.message(EditChannel.editing_chat_id)
async def save_channel_chat_id(message: Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    
    if not channel_id:
        await message.answer("Ошибка: не найден ID канала")
        await state.clear()
        return
    
    async with SessionLocal() as session:
        channel = await session.get(Channel, channel_id)
        if channel:
            channel.chat_id = message.text
            await session.commit()
            await message.answer("Chat ID канала обновлен!")
        else:
            await message.answer("Ошибка: канал не найден")
    
    await state.clear()