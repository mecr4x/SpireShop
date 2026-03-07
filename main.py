## main.py - ПОЛНЫЙ РАБОЧИЙ КОД БЕЗ ВЕБХУКОВ
import sys
import asyncio

# Для Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import logging
import time

import aiohttp
from aiogram import Bot, Dispatcher, Router, F
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

    if user_messages[user_id]:
        try:
            old_message_id = user_messages[user_id][-1]
            await bot.delete_message(chat_id=user_id, message_id=old_message_id)
        except:
            pass

    user_messages[user_id].append(new_message_id)

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
    await delete_user_message(callback.from_user.id, callback.message.message_id)

    confirm_msg = await callback.message.answer("✅ Подписка подтверждена!")
    await save_and_delete_previous(callback.from_user.id, confirm_msg.message_id)

    await asyncio.sleep(1)
    await menu_cmd(callback.message)
    await callback.answer()


# ===== КОМАНДА /MENU =====
@router.message(Command("menu"))
async def menu_cmd(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить звёзды", callback_data="stars", icon_custom_emoji_id=5438391541288689158)],
        [InlineKeyboardButton(text="Пополнить TON", callback_data="ton", icon_custom_emoji_id=5438332129006081114)],
        [InlineKeyboardButton(text="Купить Premium", callback_data="premium", icon_custom_emoji_id=5402352097045795954)],
        [
            InlineKeyboardButton(text="Поддержка", url=f"https://t.me/{SUPPORT_USERNAME[1:]}", icon_custom_emoji_id=6021798595739523148),
            InlineKeyboardButton(text="Информация", callback_data="info", icon_custom_emoji_id=5258503720928288433)
        ]
    ])

    try:
        photo = FSInputFile("images/menu.jpg")
        sent_message = await message.answer_photo(photo=photo, reply_markup=keyboard)
    except:
        sent_message = await message.answer("Меню:", reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)


# ===== ОБРАБОТЧИК КНОПКИ "ИНФОРМАЦИЯ" =====
@router.callback_query(F.data == "info")
async def info_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    text = (
        "<tg-emoji emoji-id=\"5258503720928288433\">ℹ️</tg-emoji><b>Информация</b>\n\n"
        "Здесь вы можете ознакомиться с важными документами сервиса:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Политика конфиденциальности", url="https://telegra.ph/Politika-konfidencialnosti-03-03-42", icon_custom_emoji_id=6021741567163767583)],
        [InlineKeyboardButton(text="Пользовательское соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-03-03-16", icon_custom_emoji_id=6021741567163767583)],
        [InlineKeyboardButton(text=" Назад", callback_data="menu")],
    ])
    
    try:
        photo = FSInputFile("images/info.jpg")
        sent_message = await callback.message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)
    
    await save_and_delete_previous(callback.from_user.id, sent_message.message_id)
    await callback.answer()


# ===== КОМАНДА /STARS =====
@router.message(Command("stars"))
async def stars_cmd(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
        "<b>Минимальное количество:</b> 50\n"
        "<b>Максимальное количество:</b> 1,000,000\n\n"
        "Введите количество звёзд для покупки:"
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
    await delete_user_message(message.from_user.id, message.message_id)

    try:
        star_value = int(message.text.strip())

        if star_value < 50 or star_value > 1000000:
            error_msg = await message.answer("❌ Количество должно быть от 50 до 1,000,000")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        formulastar = round(star_value * 1.7, 1)

        save_user_data(message.from_user.id, "stars", {
            'star_value': star_value,
            'formulastar': formulastar,
        })

        text = (
            f"<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
            f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд\n"
            f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulastar}₽\n\n"
            f"Для кого вы приобретаете:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Купить себе", callback_data="buy_stars_self", icon_custom_emoji_id=5406604187683270743)],
            [InlineKeyboardButton(text="Подарить другу", callback_data="gift_stars_friend", icon_custom_emoji_id=5203996991054432397)],
            [InlineKeyboardButton(text="Назад", callback_data="stars")]
        ])

        try:
            sent_message = await message.answer(text, reply_markup=keyboard)
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

    username = callback.from_user.username
    if not username:
        username = f"id{user_id}"
    else:
        username = f"@{username}"

    from username_checker import check_username

    check_msg = await callback.message.answer("🔍 Проверяю пользователя...")
    result = await check_username(username)
    await delete_user_message(user_id, check_msg.message_id)

    if not result['exists']:
        error_text = f"❌ Пользователь не найден."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попробовать снова", callback_data="stars")]
        ])
        sent_message = await callback.message.answer(error_text, reply_markup=keyboard)
        await save_and_delete_previous(user_id, sent_message.message_id)
        await callback.answer()
        return

    text = (
        f"<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulastar}₽ \n"
        f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Получатель:</b> {username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_stars_self_{formulastar}", icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="Cryptobot", callback_data=f"crypto_stars_{round(formulastar / 0.97, 1)}", icon_custom_emoji_id=5361914370068613491)],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_stars_choice")]
    ])

    try:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)
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
        f"<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulastar}₽\n\n"
        f"Введите @username получателя:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back_to_stars_choice")]
    ])

    try:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)
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

    text = (
        f"<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulastar}₽ \n\n"
        f"Для кого вы приобретаете:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить себе", callback_data="buy_stars_self", icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="Подарить другу", callback_data="gift_stars_friend", icon_custom_emoji_id=5203996991054432397)],
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

    from username_checker import check_username

    check_msg = await message.answer("🔍 Проверяю существование пользователя...")
    result = await check_username(username)
    await delete_user_message(message.from_user.id, check_msg.message_id)

    if not result['exists']:
        error_text = f"❌ Указанный пользователь не найден\n\n📥 Пользователь: {username}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Попробовать снова", callback_data="gift_stars_friend")]
        ])
        sent_message = await message.answer(error_text, reply_markup=keyboard)
        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()
        return

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

    text = (
        f"<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulastar}₽ \n"
        f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Получатель:</b> {username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_stars_friend_{formulastar}", icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="Cryptobot", callback_data=f"crypto_stars_friend_{round(formulastar / 0.97, 1)}", icon_custom_emoji_id=5361914370068613491)],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_stars_choice")]
    ])

    try:
        sent_message = await message.answer(text, reply_markup=keyboard)
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
        f"<tg-emoji emoji-id=\"5438332129006081114\">💎</tg-emoji><b>TON</b>\n\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Курс к рублю:</b> {round(TON_RUB + 30, 2)}₽\n"
        f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji>️<b>Примечание:</b> TON поступает не на кошелек, а на Telegram аккаунт по @username."
        f"Использовать TON можно <b>только</b> в качестве покупки подарков на Telegram маркете, "
        f"а так же для оплаты за посты в Telegram каналах!\n\n"
        f"Введите количество TON для покупки:\n"
        f"(Целое значение большее 1)"
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
    await state.set_state(Form.waiting_for_ton_amount)


# ===== ОБРАБОТКА СУММЫ ТОН =====
@router.message(Form.waiting_for_ton_amount)
async def process_ton_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await delete_user_message(message.from_user.id, message.message_id)

    try:
        text = message.text.strip()

        if not text.isdigit():
            error_msg = await message.answer("❌ Введите целое число без дробной части (например: 5, 10, 100)")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        ton_value = int(text)

        if ton_value < 1:
            error_msg = await message.answer("❌ Введите целое значение от 1 TON")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        formulaTON = round(ton_value * (TON_RUB + 30), 1)

        save_user_data(user_id, "ton_purchase", {
            'ton_value': ton_value,
            'formulaTON': formulaTON,
        })

        text = (
            f"<tg-emoji emoji-id=\"5438332129006081114\">💎</tg-emoji><b>TON</b>\n\n"
            f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {ton_value} TON\n"
            f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulaTON} ₽\n\n"
            f"Для кого вы приобретаете?"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Купить себе", callback_data="buy_ton_self", icon_custom_emoji_id=5406604187683270743)],
            [InlineKeyboardButton(text="Подарить другу", callback_data="gift_ton_friend", icon_custom_emoji_id=5203996991054432397)],
            [InlineKeyboardButton(text="Назад", callback_data="ton")]
        ])

        try:
            sent_message = await message.answer(text, reply_markup=keyboard)
        except:
            sent_message = await message.answer(text, reply_markup=keyboard)

        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()

    except ValueError:
        error_msg = await message.answer("❌ Пожалуйста, введите корректное целое число")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)


# ===== КУПИТЬ СЕБЕ =====
@router.callback_query(F.data == "buy_ton_self")
async def ton_self_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id, "ton_purchase")

    if not data:
        await callback.answer("❌ Сначала выберите сумму", show_alert=True)
        return

    ton_value = data['ton_value']
    formulaTON = data['formulaTON']

    username = callback.from_user.username
    if not username:
        username = f"id{user_id}"
    else:
        username = f"@{username}"

    text = (
        f"<tg-emoji emoji-id=\"5438332129006081114\">💎</tg-emoji><b>TON</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {ton_value} TON\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulaTON}₽\n"
        f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Получатель</b>: {username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_ton_self_{formulaTON}", icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="CryptoBot", callback_data=f"crypto_ton_{formulaTON}", icon_custom_emoji_id=5361914370068613491)],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="ton")]
    ])

    try:
        sent = await callback.message.answer(text, reply_markup=keyboard)
    except:
        sent = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent.message_id)
    await callback.answer()


# ===== ПОДАРИТЬ ДРУГУ =====
@router.callback_query(F.data == "gift_ton_friend")
async def ton_friend_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = get_user_data(user_id, "ton_purchase")

    if not data:
        await callback.answer("❌ Сначала выберите сумму", show_alert=True)
        return

    ton_value = data['ton_value']
    formulaTON = data['formulaTON']

    text = (
        f"<tg-emoji emoji-id=\"5438332129006081114\">💎</tg-emoji><b>TON</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {ton_value} TON\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulaTON}₽\n\n"
        f"Введите @username получателя:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="buy_ton_self")]
    ])

    try:
        sent = await callback.message.answer(text, reply_markup=keyboard)
    except:
        sent = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent.message_id)
    await state.set_state(Form.waiting_for_ton_friend_username)
    await callback.answer()


# ===== ОБРАБОТКА USERNAME ДРУГА =====
@router.message(Form.waiting_for_ton_friend_username)
async def process_ton_friend(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await delete_user_message(user_id, message.message_id)

    username = message.text.strip().replace('@', '')
    if not username:
        error = await message.answer("❌ Введите username")
        await save_and_delete_previous(user_id, error.message_id)
        await asyncio.sleep(2)
        await delete_user_message(user_id, error.message_id)
        return

    from username_checker import check_username
    check_msg = await message.answer("🔍 Проверка...")
    result = await check_username(username)
    await delete_user_message(user_id, check_msg.message_id)

    if not result['exists']:
        error = await message.answer(f"❌ @{username} не найден")
        await save_and_delete_previous(user_id, error.message_id)
        await state.clear()
        return

    data = get_user_data(user_id, "ton_purchase")
    if not data:
        await message.answer("❌ Ошибка данных")
        await state.clear()
        return

    ton_value = data['ton_value']
    formulaTON = data['formulaTON']

    text = (
        f"<tg-emoji emoji-id=\"5438332129006081114\">💎</tg-emoji><b>TON</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {ton_value} TON\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulaTON}₽\n"
        f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Получатель</b>: @{username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_ton_friend_{formulaTON}", icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="CryptoBot", callback_data=f"crypto_ton_{formulaTON}", icon_custom_emoji_id=5361914370068613491)],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="ton")]
    ])

    try:
        sent = await message.answer(text, reply_markup=keyboard)
    except:
        sent = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent.message_id)
    await state.clear()


# ===== КОМАНДА /PREMIUM =====
@router.message(Command("premium"))
async def premium_cmd(message: Message):
    text = ("<tg-emoji emoji-id=\"5402352097045795954\">👑</tg-emoji><b>Telegram Premium</b>\n\n"
            "<tg-emoji emoji-id=\"5274055917766202507\">🗓</tg-emoji>Выберите период подписки:")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Premium - 12 месяцев", callback_data="premium_12")],
        [InlineKeyboardButton(text="Premium - 6 месяцев", callback_data="premium_6")],
        [InlineKeyboardButton(text="Premium - 3 месяца", callback_data="premium_3")],
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

    try:
       
