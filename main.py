## main.py - ПОЛНЫЙ КОД С ПРОВЕРКОЙ ПОДПИСКИ
import sys
import asyncio

# Для Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import logging
import time

import aiohttp
import re
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
import json
import time


# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8236812443:AAGsoEmE7u9q5eBpKTQ3vlbp4IregP9-oHY"
ADMIN_ID = 887261650
ADMIN_CHANNEL = '@spireshop01'  # канал для подписки
SUPPORT_USERNAME = '@adamyan_ss'
TON_WALLET = 'UQAL5Y75ykdUsMmW5FgnxKJyz1-njyS_oNuN1Lp2_hgNundO'

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
TON_RUB = 140

# ===== ХРАНИЛИЩЕ ДЛЯ УДАЛЕНИЯ СООБЩЕНИЙ =====
user_messages = {}
async def save_and_delete_previous(user_id: int, new_message_id: int):
    """Сохранить новое сообщение и удалить старое"""
    if user_id not in user_messages:
        user_messages[user_id] = []

    # Удаляем предыдущее сообщение если есть
    if user_messages[user_id]:
        try:
            old_message_id = user_messages[user_id][-1]
            await bot.delete_message(chat_id=user_id, message_id=old_message_id)
        except:
            pass

    # Сохраняем новое
    user_messages[user_id].append(new_message_id)

    # Храним только последние 3 сообщения
    if len(user_messages[user_id]) > 3:
        user_messages[user_id] = user_messages[user_id][-3:]


async def delete_user_message(user_id: int, message_id: int):
    """Удалить конкретное сообщение"""
    try:
        await bot.delete_message(chat_id=user_id, message_id=message_id)
        if user_id in user_messages and message_id in user_messages[user_id]:
            user_messages[user_id].remove(message_id)
    except:
        pass


# ===== ПРОВЕРКА ПОДПИСКИ =====
async def check_subscription(user_id: int) -> bool:
    """Проверяет, подписан ли пользователь на канал"""
    try:
        member = await bot.get_chat_member(ADMIN_CHANNEL, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

async def require_subscription_callback(callback: CallbackQuery) -> bool:
    """Проверяет подписку и показывает всплывающее окно если нет"""
    if not await check_subscription(callback.from_user.id):
        await callback.answer(
            "❌ Сначала подпишитесь на канал @spireshop01",
            show_alert=True
        )
        return False
    return True


# ===== СОСТОЯНИЯ =====
class Form(StatesGroup):
    waiting_for_stars_amount = State()
    waiting_for_friend_username = State()
    waiting_for_ton_address = State()
    waiting_for_ton_amount = State()  # 👈 ЭТО ДОЛЖНО БЫТЬ
    waiting_for_ton_friend_username = State()
    waiting_for_premium_friend = State()


# ===== ХРАНИЛИЩЕ ДАННЫХ =====
user_data = {}


def save_user_data(user_id, key, value):
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id][key] = value


def get_user_data(user_id, key):
    return user_data.get(user_id, {}).get(key)

async def get_ton_price():
    """Получение курса TON"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    'https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=rub',
                    timeout=5
            ) as response:
                data = await response.json()
                return data['the-open-network']['rub']
    except:
        return 140

# ===== КОМАНДА /START =====
@router.message(Command("start"))
async def start_cmd(message: Message):
    text = (
        "<b>Добро пожаловать!</b>\n\n"
        "<b>Spire</b> — магазин для покупки Telegram Stars, TON и Premium "
        "дешевле, чем в приложении и без верификации.\n\n"
        "<tg-emoji emoji-id=\"5274099962655816924\">❗️</tg-emoji><b>Чтобы продолжить подпишитесь на наш канал:</b>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/{ADMIN_CHANNEL[1:]}")],
        [InlineKeyboardButton(text="✅ Проверить Подписку", callback_data="check_sub")]
    ])

    try:
        photo = FSInputFile("images/start.jpg")
        sent_message = await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)


# ===== ПРОВЕРКА ПОДПИСКИ =====
@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    # Удаляем сообщение с кнопкой
    await delete_user_message(callback.from_user.id, callback.message.message_id)

    # Отправляем подтверждение
    confirm_msg = await callback.message.answer("✅ Подписка подтверждена!")
    await save_and_delete_previous(callback.from_user.id, confirm_msg.message_id)

    # Показываем меню
    await asyncio.sleep(1)
    await menu_cmd(callback.message)
    await callback.answer()


# ===== КОМАНДА /MENU =====
@router.message(Command("menu"))
async def menu_cmd(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить звёзды", callback_data="stars", icon_custom_emoji_id = 5438391541288689158)],
        [InlineKeyboardButton(text="Пополнить TON", callback_data="ton", icon_custom_emoji_id = 5438332129006081114)],
        [InlineKeyboardButton(text="Купить Premium", callback_data="premium", icon_custom_emoji_id =5402352097045795954)],
        [
            InlineKeyboardButton(text="Поддержка", url=f"https://t.me/{SUPPORT_USERNAME[1:]}", icon_custom_emoji_id = 6021798595739523148),
            InlineKeyboardButton(text="Информация", callback_data="info", icon_custom_emoji_id = 5258503720928288433)
        ]
    ])

    try:
        photo = FSInputFile("images/menu.jpg")
        sent_message = await message.answer_photo(photo=photo, reply_markup=keyboard)
    except:
        sent_message = await message.answer("Меню:", reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)



# ===== ЗАПУСК =====
async def main():
    # 👇 СНАЧАЛА ПРИНУДИТЕЛЬНО УДАЛЯЕМ ВЕБХУК
    try:
        await bot.delete_webhook()
        print("✅ Вебхук удалён")
    except Exception as e:
        print(f"⚠️ Ошибка при удалении вебхука: {e}")
    
    from username_checker import ensure_client
    await ensure_client()
    print("✅ Telethon готов к работе")

    print("=" * 50)
    print("🤖 Бот запускается...")
    print("🔍 TON Checker: API проверка активирована")
    print("👤 Username Checker: Telethon проверка в отдельном файле")
    print("🧹 Удаление сообщений: Включено")
    print("=" * 50)

    try:
        global TON_RUB
        TON_RUB = await get_ton_price()
        print(f"💰 Курс TON: {TON_RUB}₽")

        me = await bot.get_me()
        print(f"✅ Бот: @{me.username}")

        print("=" * 50)
        print("📋 Команды:")
        print("/start /menu /stars /ton /premium")
        print("=" * 50)
        print("⏳ Ожидаю сообщений...")
        print("=" * 50)

        await dp.start_polling(bot, skip_updates=True)

    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
