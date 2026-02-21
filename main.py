## main.py - рабочий код с проверкой TON и удалением сообщений
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

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8236812443:AAGsoEmE7u9q5eBpKTQ3vlbp4IregP9-oHY"
ADMIN_CHANNEL = '@spireshop01'
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


# ===== СОСТОЯНИЯ =====
class Form(StatesGroup):
    waiting_for_stars_amount = State()
    waiting_for_friend_username = State()
    waiting_for_ton_address = State()
    waiting_for_ton_amount = State()
    waiting_for_premium_friend = State()


# ===== ХРАНИЛИЩЕ ДАННЫХ =====
user_data = {}


def save_user_data(user_id, key, value):
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id][key] = value


def get_user_data(user_id, key):
    return user_data.get(user_id, {}).get(key)


# ===== ФУНКЦИИ ДЛЯ TON =====
def is_valid_ton_format(address: str) -> bool:
    """Проверка формата адреса TON"""
    if not address or not isinstance(address, str):
        return False

    address = address.strip()

    # Проверка длины
    if len(address) < 48 or len(address) > 67:
        return False

    # Проверка префиксов
    valid_prefixes = ['UQ', 'EQ', 'kQ', '0Q']
    return any(address.startswith(prefix) for prefix in valid_prefixes)


async def check_ton_address_exists(address: str) -> tuple[bool, str]:
    """Проверка существования адреса TON через API"""
    try:
        async with aiohttp.ClientSession() as session:
            # Используем TonCenter API
            url = "https://toncenter.com/api/v2/getAddressInformation"
            params = {"address": address}

            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        return True, "✅ Адрес существует и валиден"
                    else:
                        return False, "❌Указанный вами адрес не корректен"
                else:
                    return False, "❌Указанный вами адрес не корректен"
    except Exception as e:
        return False, f"❌ Ошибка сети: {str(e)}"


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
        "Добро пожаловать!\n\n"
        "Spire — магазин для покупки Telegram Stars, TON и Premium "
        "дешевле, чем в приложении и без верификации.\n\n"
        "❗Чтобы продолжить подпишитесь на наш канал:"
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
        [InlineKeyboardButton(text="⭐️ Купить звёзды", callback_data="stars")],
        [InlineKeyboardButton(text="💎 Купить TON", callback_data="ton")],
        [InlineKeyboardButton(text="👑 Купить Premium", callback_data="premium")],
        [InlineKeyboardButton(text="🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME[1:]}")]
    ])

    try:
        photo = FSInputFile("images/menu.jpg")
        sent_message = await message.answer_photo(photo=photo, reply_markup=keyboard)
    except:
        sent_message = await message.answer(reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)


# ===== КОМАНДА /STARS =====
@router.message(Command("stars"))
async def stars_cmd(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "⭐️Telegram Stars\n\n"
        "💰Курс к рублю: 1.7₽\n"
        "Минимальное количество: 50\n"
        "Максимальное количество: 1,000,000\n\n"
        "✏️Введите количество звезд для покупки:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

    try:
        photo = FSInputFile("images/stars.jpg")
        sent_message = await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.set_state(Form.waiting_for_stars_amount)


# ===== ОБРАБОТКА КОЛИЧЕСТВА ЗВЁЗД =====
@router.message(Form.waiting_for_stars_amount)
async def process_stars_amount(message: Message, state: FSMContext):
    # Удаляем сообщение пользователя
    await delete_user_message(message.from_user.id, message.message_id)

    try:
        star_value = int(message.text.strip())

        if star_value < 50 or star_value > 1000000:
            error_msg = await message.answer("❌ Количество должно быть от 50 до 1,000,000")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        # Расчет стоимости
        formulastar = round(star_value * 1.7, 1)

        # Сохраняем данные
        save_user_data(message.from_user.id, "stars", {
            'star_value': star_value,
            'formulastar': formulastar,
        })

        text = (
            f"⭐️Telegram Stars\n\n"
            f"❗️Количество: {star_value}\n"
            f"💰 Стоимость: {formulastar}₽\n\n"
            f"Для кого вы приобретаете:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💫 Купить себе", callback_data="buy_stars_self")],
            [InlineKeyboardButton(text="🎁 Подарить другу", callback_data="gift_stars_friend")],
            [InlineKeyboardButton(text="Назад", callback_data="stars")]
        ])

        try:
            sent_message = await message.answer_photo(caption=text, reply_markup=keyboard)
        except:
            sent_message = await message.answer(text, reply_markup=keyboard)

        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()

    except ValueError:
        error_msg = await message.answer("❌ Пожалуйста, введите корректное число")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)

# ===== КНОПКА "КУПИТЬ СЕБЕ" =====
@router.callback_query(F.data == "buy_stars_self")
async def buy_stars_self_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    stars_data = get_user_data(user_id, "stars")

    if not stars_data:
        await callback.answer("❌ Сначала выберите количество звёзд", show_alert=True)
        return

    star_value = stars_data['star_value']
    formulastar = stars_data['formulastar']

    # Получаем username
    username = callback.from_user.username
    if not username:
        username = f"id{user_id}"
    else:
        username = f"@{username}"

    # ===== ПРОВЕРЯЕМ ТОЛЬКО СУЩЕСТВОВАНИЕ USERNAME =====
    from username_checker import check_username

    check_msg = await callback.message.answer("🔍 Проверяю пользователя...")
    result = await check_username(username)
    await delete_user_message(user_id, check_msg.message_id)

    if not result['exists']:
        # Username не существует
        error_text = f"❌Пользователь не найден."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попробовать снова", callback_data="stars")]
        ])
        sent_message = await callback.message.answer(error_text, reply_markup=keyboard)
        await save_and_delete_previous(user_id, sent_message.message_id)
        await callback.answer()
        return

    text = (
        f"⭐️Telegram Stars\n\n"
        f"❗️Количество: {star_value} звёзд\n"
        f"💰 Стоимость: {formulastar}₽ \n"
        f"👤 Получатель: {username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦СБП", callback_data=f"sbp_stars_{formulastar}")],
        [InlineKeyboardButton(text="💎Cryptobot", callback_data=f"crypto_stars_{round (formulastar /0.97,1)}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_stars_choice")]
    ])

    try:
        sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
    except:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent_message.message_id)
    await callback.answer()

# ===== КНОПКА "ПОДАРИТЬ ДРУГУ" =====
@router.callback_query(F.data == "gift_stars_friend")
async def gift_stars_friend_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    stars_data = get_user_data(user_id, "stars")

    if not stars_data:
        await callback.answer("❌ Сначала выберите количество звёзд", show_alert=True)
        return

    star_value = stars_data['star_value']
    formulastar = stars_data['formulastar']

    text = (
        f"⭐️Telegram Stars\n\n"
        f"❗️Количество: {star_value} звёзд\n"
        f"💰Стоимость: {formulastar}₽ \n\n"
        f"👤Введите @username получателя:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back_to_stars_choice")]
    ])

    try:
        sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
    except:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent_message.message_id)
    await state.set_state(Form.waiting_for_friend_username)
    await callback.answer()


# ===== ВОЗВРАТ К ВЫБОРУ ПОЛУЧАТЕЛЯ =====
@router.callback_query(F.data == "back_to_stars_choice")
async def back_to_stars_choice_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    stars_data = get_user_data(user_id, "stars")

    if not stars_data:
        await callback.answer("❌ Данные не найдены", show_alert=True)
        return

    star_value = stars_data['star_value']
    formulastar = stars_data['formulastar']
    star_ton = stars_data['star_ton']

    text = (
        f"⭐️Telegram Stars\n\n"
        f"❗️Количество: {star_value} звёзд\n"
        f"💰 Стоимость: {formulastar}₽ \n\n"
        f"Для кого вы приобретаете:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💫 Купить себе", callback_data="buy_stars_self")],
        [InlineKeyboardButton(text="🎁 Подарить другу", callback_data="gift_stars_friend")],
        [InlineKeyboardButton(text="Назад", callback_data="stars")]
    ])

    try:
        photo = FSInputFile("images/stars.jpg")
        sent_message = await callback.message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent_message.message_id)
    await callback.answer()


# ===== ОБРАБОТКА USERNAME ДЛЯ ЗВЁЗД =====
@router.message(Form.waiting_for_friend_username)
async def process_friend_username(message: Message, state: FSMContext):
    await delete_user_message(message.from_user.id, message.message_id)

    username = message.text.strip()
    if not username:
        error_msg = await message.answer("❌ Пожалуйста, введите username")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)
        return

    # ===== ПРОВЕРКА ЧЕРЕЗ username_checker.py =====
    from username_checker import check_username

    # Проверяем существует ли такой username
    check_msg = await message.answer("🔍 Проверяю существование пользователя...")
    result = await check_username(username)
    await delete_user_message(message.from_user.id, check_msg.message_id)

    if not result['exists']:
        # Юзернейм не существует
        error_text = f"❌Указанный пользователь не найден\n\n📥Пользователь: {username}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попробовать снова", callback_data="gift_stars_friend")]
        ])
        sent_message = await message.answer(error_text, reply_markup=keyboard)
        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()
        return

    # Юзернейм существует - продолжаем
    if not username.startswith('@'):
        username = f"@{username}"

    user_id = message.from_user.id
    stars_data = get_user_data(user_id, "stars")

    if not stars_data:
        await message.answer("❌ Ошибка данных")
        await state.clear()
        return

    star_value = stars_data['star_value']
    formulastar = stars_data['formulastar']
    star_ton = stars_data['star_ton']

    text = (
        f"⭐️Telegram Stars\n\n"
        f"❗️Количество: {star_value} звёзд\n"
        f"💰 Стоимость: {formulastar}₽\n"
        f"👤 Получатель: {username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦СБП", callback_data=f"sbp_stars_friend_{formulastar}")],
        [InlineKeyboardButton(text="💎Cryptobot", callback_data=f"crypto_stars_friend_{round (formulastar /0.97,1)}")],
        [InlineKeyboardButton(text="❌Отмена", callback_data="back_to_stars_choice")]
    ])

    try:
        sent_message = await message.answer_photo(caption=text, reply_markup=keyboard)
    except:
        sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.clear()


# ===== КОМАНДА /TON =====
@router.message(Command("ton"))
async def ton_cmd(message: Message, state: FSMContext):
    await state.clear()
    global TON_RUB
    TON_RUB = await get_ton_price()

    text = (
        f"💎 TON\n\n"
        f"💰Курс к рублю: {TON_RUB + 11}₽\n"
        f"Минимальное количество: 1 TON\n\n"
        f"✏️Введите адрес кошелька для получения TON:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

    try:
        photo = FSInputFile("images/ton.jpg")
        sent_message = await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.set_state(Form.waiting_for_ton_address)


# ===== ОБРАБОТКА АДРЕСА TON (с API проверкой) =====
@router.message(Form.waiting_for_ton_address)
async def process_ton_address(message: Message, state: FSMContext):
    await delete_user_message(message.from_user.id, message.message_id)

    address = message.text.strip()

    # Проверка формата
    if not is_valid_ton_format(address):
        text = (
            f"❌Указанный вами адрес не корректен\n\n"
            f"📥Адрес: {address}"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попробовать снова", callback_data="ton")]
        ])

        sent_message = await message.answer(text, reply_markup=keyboard)
        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()
        return

    # Проверка существования через API
    checking_msg = await message.answer("⏳ Проверяю адрес через сеть TON...")

    exists, feedback = await check_ton_address_exists(address)

    await delete_user_message(message.from_user.id, checking_msg.message_id)

    if not exists:
        text = f"{feedback}\n\n📥Адрес:{address}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Попробовать снова", callback_data="ton")]
        ])

        sent_message = await message.answer(text, reply_markup=keyboard)
        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()
        return

    # Адрес валиден и существует
    save_user_data(message.from_user.id, "ton_address", address)

    text = (
        f"💎 TON\n\n"
        f"📥 Адрес: {address}\n\n"
        f"✏️ Теперь введите сумму в TON для покупки:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="ton")]
    ])

    sent_message = await message.answer(text, reply_markup=keyboard)
    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.set_state(Form.waiting_for_ton_amount)


# ===== ОБРАБОТКА СУММЫ TON =====
@router.message(Form.waiting_for_ton_amount)
async def process_ton_amount(message: Message, state: FSMContext):
    await delete_user_message(message.from_user.id, message.message_id)

    try:
        ton_value = float(message.text.strip().replace(',', '.'))

        if ton_value < 1:
            error_msg = await message.answer("❌ Минимальное количество: 1 TON")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        # Расчет стоимости
        formulaTON = round(ton_value * (TON_RUB + 11), 1)

        # Получаем адрес
        user_id = message.from_user.id
        address = get_user_data(user_id, "ton_address")

        if not address:
            await message.answer("❌ Ошибка: адрес не найден. Начните заново.")
            await state.clear()
            return

        # Сохраняем данные
        save_user_data(user_id, "ton_purchase", {
            'ton_value': ton_value,
            'formulaTON': formulaTON,
            'address': address
        })

        text = (
            f"💎TON\n\n"
            f"❗Количество: {ton_value} TON\n"
            f"💰Стоимость: {formulaTON} ₽\n"
            f"📥Адрес получения: {address}\n\n"
            f"Выберите способ оплаты:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦 СБП", callback_data=f"sbp_ton_{formulaTON}")],
            [InlineKeyboardButton(text="💎Cryptobot", callback_data=f"crypto_ton_{round(formulaTON/0.97,1)}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="ton")]
        ])

        try:
            sent_message = await message.answer_photo(caption=text, reply_markup=keyboard)
        except:
            sent_message = await message.answer(text, reply_markup=keyboard)

        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()

    except ValueError:
        error_msg = await message.answer("❌ Пожалуйста, введите корректное число (например: 1.5 или 2)")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)


# ===== КОМАНДА /PREMIUM =====
@router.message(Command("premium"))
async def premium_cmd(message: Message):
    text = "👑Telegram Premium\n\n🗓Выберите период подписки:"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Premium - 12 месяцев", callback_data="premium_12")],
        [InlineKeyboardButton(text="Premium - 6 месяцев", callback_data="premium_6")],
        [InlineKeyboardButton(text="Premium - 3 месяца", callback_data="premium_3")],
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

    try:
        photo = FSInputFile("images/premium.jpg")
        sent_message = await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)


# ===== КНОПКИ PREMIUM =====
@router.callback_query(F.data.startswith("premium_"))
async def premium_period_callback(callback: CallbackQuery, state: FSMContext):
    periods = {
        "premium_12": "12 месяцев",
        "premium_6": "6 месяцев",
        "premium_3": "3 месяца"
    }

    prices = {
        "premium_12": 3000,
        "premium_6": 1700,
        "premium_3": 1300
    }

    period = periods.get(callback.data, "3 месяца")
    priceprem = prices.get(callback.data, 1300)

    save_user_data(callback.from_user.id, "premium", {
        'period': period,
        'priceprem': priceprem
    })

    text = (
        f"👑 Telegram Premium\n\n"
        f"📅Срок: {period}\n"
        f"💰Стоимость: {priceprem}₽\n\n"
        f"Для кого вы приобретаете:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💫 Купить себе", callback_data="buy_premium_self")],
        [InlineKeyboardButton(text="🎁 Подарить другу", callback_data="gift_premium_friend")],
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

    try:
        sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
    except:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(callback.from_user.id, sent_message.message_id)
    await callback.answer()

# ===== КНОПКА "КУПИТЬ PREMIUM СЕБЕ" =====
@router.callback_query(F.data == "buy_premium_self")
async def buy_premium_self_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    premium_data = get_user_data(user_id, "premium")

    if not premium_data:
        await callback.answer("❌Сначала выберите период", show_alert=True)
        return

    period = premium_data['period']
    priceprem = premium_data['priceprem']

    # Получаем username
    username = callback.from_user.username
    if not username:
        username = f"id{user_id}"
    else:
        username = f"@{username}"

    # ===== ПРОВЕРЯЕМ PREMIUM СТАТУС ПОЛЬЗОВАТЕЛЯ =====
    from username_checker import check_username

    check_msg = await callback.message.answer("🔍 Проверяю статус Premium...")
    result = await check_username(username)
    await delete_user_message(user_id, check_msg.message_id)

    if result.get('exists') and result.get('premium'):
        # У пользователя уже есть Premium
        text = (
            f"❌У вас уже активирован Telegram Premium\n\n"
            f"Пользователь: {username}\n\n"
            f"Premium оформить нельзя, так как у вас уже есть активированная подписка."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Подарить другу", callback_data="gift_premium_friend")],
            [InlineKeyboardButton(text="Назад", callback_data="premium")]
        ])

        try:
            sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
        except:
            sent_message = await callback.message.answer(text, reply_markup=keyboard)

    else:
        # У пользователя НЕТ Premium - можно оформлять
        text = (
            f"👑Telegram Premium\n\n"
            f"📅Срок: {period}\n"
            f"💰Стоимость: {priceprem}₽\n"
            f"👤Получатель: {username}\n\n"
            f"Выберите способ оплаты:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦СБП", callback_data=f"sbp_premium_{priceprem}")],
            [InlineKeyboardButton(text="💎Cryptobot", callback_data=f"crypto_premium_{round(priceprem /0.97,1)}")],
            [InlineKeyboardButton(text="❌Отмена", callback_data="premium")]
        ])

        try:
            sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
        except:
            sent_message = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent_message.message_id)
    await callback.answer()

# ===== КНОПКА "ПОДАРИТЬ PREMIUM ДРУГУ" =====
@router.callback_query(F.data == "gift_premium_friend")
async def gift_premium_friend_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    premium_data = get_user_data(user_id, "premium")

    if not premium_data:
        await callback.answer("❌ Сначала выберите период", show_alert=True)
        return

    period = premium_data['period']
    priceprem = premium_data['priceprem']

    text = (
        f"👑Telegram Premium\n\n"
        f"📆Срок: {period}\n"
        f"💰Стоимость: {priceprem}₽\n\n"
        f"👤Введите @username получателя:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="premium")]
    ])

    try:
        sent_message = await callback.message.answer_photo (caption=text, reply_markup=keyboard)
    except:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent_message.message_id)
    await state.set_state(Form.waiting_for_premium_friend)
    await callback.answer()


# ===== ОБРАБОТКА USERNAME ДЛЯ PREMIUM =====
@router.message(Form.waiting_for_premium_friend)
async def process_premium_friend(message: Message, state: FSMContext):
    await delete_user_message(message.from_user.id, message.message_id)

    username = message.text.strip()
    if not username:
        error_msg = await message.answer("❌Пожалуйста, введите username")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)
        return

    # ===== ПРОВЕРКА ЧЕРЕЗ username_checker.py =====
    from username_checker import check_username

    # Проверяем существует ли такой username
    check_msg = await message.answer("🔍 Проверяю пользователя...")
    result = await check_username(username)
    await delete_user_message(message.from_user.id, check_msg.message_id)

    if not result['exists']:
        # Юзернейм не существует
        error_text = f"❌Пользователь не найден.\n\nПользователь: {username}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попробовать снова", callback_data="gift_premium_friend")]
        ])
        sent_message = await message.answer(error_text, reply_markup=keyboard)
        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()
        return

    # Юзернейм существует
    if not username.startswith('@'):
        username = f"@{username}"

    user_id = message.from_user.id
    premium_data = get_user_data(user_id, "premium")

    if not premium_data:
        await message.answer("❌Ошибка данных")
        await state.clear()
        return

    period = premium_data['period']
    priceprem = premium_data['priceprem']

    # ===== ПРОВЕРЯЕМ PREMIUM СТАТУС =====
    if result.get('premium'):
        # У пользователя уже есть Premium
        text = (
            f"❌У пользователя уже активирован Telegram Premium\n\n"
            f"Пользователь: {username}\n\n"
            f"Premium оформить нельзя, так как есть активированная подписка."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попробовать снова", callback_data="premium")]
        ])

        try:

            sent_message = await message.answer_photo( caption=text, reply_markup=keyboard)
        except:
            sent_message = await message.answer(text, reply_markup=keyboard)

    else:
        # У пользователя НЕТ Premium - можно оформлять
        text = (
            f"👑Telegram Premium\n\n"
            f"📆Срок: {period}\n"
            f"💰Стоимость: {priceprem}₽\n"
            f"👤Пользователь: {username}\n\n"
            f"Выберите способ оплаты:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦СБП", callback_data=f"sbp_premium_{priceprem}")],
            [InlineKeyboardButton(text="💎Cryptobot", callback_data=f"crypto_premium_{round(priceprem /0.97,1)}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="premium")]
        ])

        try:
            sent_message = await message.answer_photo(caption=text, reply_markup=keyboard)
        except:
            sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.clear()

# ===== ОБРАБОТКА КНОПОК МЕНЮ =====
@router.callback_query(F.data == "menu")
async def menu_btn(callback: CallbackQuery):
    await menu_cmd(callback.message)
    await callback.answer()


@router.callback_query(F.data == "stars")
async def stars_btn(callback: CallbackQuery, state: FSMContext):
    await stars_cmd(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "ton")
async def ton_btn(callback: CallbackQuery, state: FSMContext):
    await ton_cmd(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "premium")
async def premium_btn(callback: CallbackQuery):
    await premium_cmd(callback.message)
    await callback.answer()


# ===== ОПЛАТА =====
@router.callback_query(F.data.startswith("crypto_"))
async def crypto_payment(callback: CallbackQuery):
    user_id = callback.from_user.id
    data_parts = callback.data.split("_")

    if len(data_parts) >= 3:
        amount = float(data_parts[2])
        payment_type = data_parts[1]
    else:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # Создаем описание
    if payment_type == "stars":
        stars_data = get_user_data(user_id, "stars")
        description = f"⭐Telegram Stars"
    elif payment_type == "premium":
        premium_data = get_user_data(user_id, "premium")
        description = f"👑Telegram Premium"
    elif payment_type == "ton":
        ton_data = get_user_data(user_id, "ton_purchase")
        description = f"💎TON"
    else:
        description = f"Оплата {amount/0.97}₽"

    # Создаем счет
    wait_msg = await callback.message.answer("Создаю счет...")

    from username_checker import create_crypto_invoice
    result = await create_crypto_invoice(amount, description, f"{payment_type}_{user_id}")

    await delete_user_message(user_id, wait_msg.message_id)

    if result["success"]:
        # Сохраняем информацию о платеже для отслеживания
        if user_id not in user_data:
            user_data[user_id] = {}
        if "pending_invoices" not in user_data[user_id]:
            user_data[user_id]["pending_invoices"] = {}

        user_data[user_id]["pending_invoices"][result["invoice_id"]] = {
            "type": payment_type,
            "amount": amount/0.97,
            "time": time.time(),
            "notified": False
        }

        # Запускаем фоновую проверку
        asyncio.create_task(track_payment(user_id, result["invoice_id"], payment_type))

        # Простая кнопка без "Я оплатил"
        text = (
            f" {description}\n\n"
            f"❗Коммисия: 3%\n"
            f"💰Сумма: {round(amount/0.97,1)} ₽*\n"
            f"⏱ Счет действителен 1 час"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Оплатить {amount*1.03}₽", url=result["pay_url"])],
            [InlineKeyboardButton(text="❌Отмена", callback_data=payment_type)]
        ])

        # Отправляем сообщение
        try:
            if payment_type == "stars":
                sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard, parse_mode="Markdown")
            elif payment_type == "premium":
                sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard, parse_mode="Markdown")
            elif payment_type == "ton":
                sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard, parse_mode="Markdown")
            else:
                sent_message = await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        except:
            sent_message = await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

        await save_and_delete_previous(user_id, sent_message.message_id)
    else:
        await callback.message.answer(f"❌Ошибка: {result.get('error', 'Неизвестная ошибка')}")

    await callback.answer()

    # ===== ФОНОВАЯ ПРОВЕРКА ПЛАТЕЖЕЙ =====


async def track_payment(user_id: int, invoice_id: str, payment_type: str):
    """Проверяет статус платежа каждые 10 секунд"""
    from username_checker import check_invoice_status

    for _ in range(36):  # 6 минут
        await asyncio.sleep(10)

        status = await check_invoice_status(invoice_id)
        if status.get("status") == "paid":
            await bot.send_message(
                user_id,
                f"✅ Оплата подтверждена! Спасибо за покупку!"
            )
            # Здесь можно добавить активацию товара
            break


async def check_invoice_status(invoice_id: str):
    """Проверяет статус счета в CryptoBot"""
    from username_checker import CRYPTO_TOKEN
    import aiohttp

    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_TOKEN}
    params = {"invoice_ids": invoice_id}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            data = await resp.json()
            if data.get("ok") and data["result"]["items"]:
                return {"status": data["result"]["items"][0]["status"]}
    return {"status": "unknown"}

# ===== ЗАПУСК =====
async def main():
    # Подключаем Telethon при запуске бота
    from username_checker import ensure_client
    await ensure_client()
    print("✅ Telethon готов к работе")
    logging.basicConfig(level=logging.INFO)

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
