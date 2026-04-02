import asyncio
import sys
import time

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiohttp
from aiogram import Bot, Dispatcher, Router, F  # 👈 Router отсюда!
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
import json
    
# Создаём роутер
router = Router()

# ===== ДЛЯ АДМИНКИ =====
user_ids = set()  # множество для хранения ID всех пользователей
admin_commands = {}  # для хранения временных данных

# ===== СОХРАНЕНИЕ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ =====
@router.message(F.text)
async def save_all_users(message: Message):
    user_ids.add(message.from_user.id)

@router.callback_query(F.text)
async def save_all_users_callback(callback: CallbackQuery):
    user_ids.add(callback.from_user.id)

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8236812443:AAGa3VCHldDpzLJbK6U7VBOncnmbHIanFYI"
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

# ===== ЦЕНЫ (можно менять через админку) =====
PRICES = {
    "stars": 1.65,           # цена за звезду
    "premium_12": 2999,
    "premium_6": 1699,
    "premium_3": 1299,
    "ton_markup": 30,       # наценка на TON
}


# ===== СОСТОЯНИЯ =====
class Form(StatesGroup):
    waiting_for_stars_amount = State()
    waiting_for_friend_username = State()
    waiting_for_ton_address = State()
    waiting_for_ton_amount = State()  # 👈 ЭТО ДОЛЖНО БЫТЬ
    waiting_for_ton_friend_username = State()
    waiting_for_premium_friend = State()
    waiting_broadcast_text = State()


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

    # Показываем меню
    await asyncio.sleep(1)
    await menu_cmd(callback.message)
    await callback.answer()


# ===== КОМАНДА /MENU =====
@router.message(Command("menu"))
async def menu_cmd(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить звёзды", callback_data="stars", icon_custom_emoji_id=5438391541288689158)],
        [InlineKeyboardButton(text="Пополнить TON", callback_data="ton", icon_custom_emoji_id=5438332129006081114)],
        [InlineKeyboardButton(text="Купить Premium", callback_data="premium",
                              icon_custom_emoji_id=5402352097045795954)],
        [InlineKeboardButton(text="Купить подарки", callback_data="nft", icon_custom_emoji_id=5380006756594243067)],
                             
        [
            InlineKeyboardButton(text="Поддержка", url=f"https://t.me/{SUPPORT_USERNAME[1:]}",
                                 icon_custom_emoji_id=6021798595739523148),
            InlineKeyboardButton(text="Информация", callback_data="info", icon_custom_emoji_id=5258503720928288433)
        ]
    ])

    try:
        photo = FSInputFile("images/menu.jpg")
        sent_message = await message.answer_photo(photo=photo, reply_markup=keyboard)
    except:
        sent_message = await message.answer(reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)


# ===== ОБРАБОТЧИК КНОПКИ "ИНФОРМАЦИЯ" =====
@router.callback_query(F.data == "info")
async def info_callback(callback: CallbackQuery, state: FSMContext):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    await state.clear()

    text = (
        "<tg-emoji emoji-id=\"5258503720928288433\">ℹ️</tg-emoji><b>Информация</b>\n\n"
        "Здесь вы можете ознакомиться с важными документами сервиса:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Политика конфиденциальности",
                              url="https://telegra.ph/Politika-konfidencialnosti-03-03-42",
                              icon_custom_emoji_id=6021741567163767583)],
        [InlineKeyboardButton(text="Пользовательское соглашение",
                              url="https://telegra.ph/Polzovatelskoe-soglashenie-03-03-16",
                              icon_custom_emoji_id=6021741567163767583)],
        [InlineKeyboardButton(text=" Назад", callback_data="back_to_menu")],
    ])
    # Отправляем сообщение
    try:
        photo = FSInputFile("images/info.jpg")
        sent_message = await callback.message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(callback.from_user.id, sent_message.message_id)
    await callback.answer()

@router.message(Command("nft"))
async def nft_cmd(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "<tg-emoji emoji-id=\"5380006756594243067\">💎</tg-emoji><b>Подарки</b>\n\n"
        "Выберите подарок из списка ниже:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Новогодняя елка | 60₽", icon_custom_emoji_id=5346117566253276549, callback_data="gift_christmastree")],
        [InlineKeyboardButton(text="Новогодний мишка | 60₽", icon_custom_emoji_id=5379850046122527013, callback_data="gift_newyearbear")],
        [InlineKeyboardButton(text="Мишка 14 февраля | 60₽", icon_custom_emoji_id=5224509179334529299, callback_data="gift_14bear")],
        [InlineKeyboardButton(text="Сердце 14 февраля | 60₽", icon_custom_emoji_id=5224648868850863664, callback_data="gift_14heart")],
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

    sent_message = await message.answer(text, reply_markup=keyboard)
    
    await save_and_delete_previous(message.from_user.id, sent_message.message_id)


# ===== ОБРАБОТЧИК ВЫБОРА ПОДАРКА =====
@router.callback_query(F.data.startswith("gift_"))
async def gift_selection(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # Карта подарков
    gifts = {
        "gift_christmastree": {"name": "Новогодняя елка", "price": 60, "gift_id": 5956217000635139069},
        "gift_newyearbear": {"name": "Новогодний мишка", "price": 60, "gift_id": 5922558454332916696},
        "gift_14bear": {"name": "Мишка 14 февраля", "price": 60, "gift_id": 5800655655995968830},
        "gift_14heart": {"name": "Сердце 14 февраля", "price": 60, "gift_id": 5801108895304779062},
    }
    
    gift_key = callback.data
    gift_info = gifts.get(gift_key)
    
    if not gift_info:
        await callback.answer("❌ Подарок не найден", show_alert=True)
        return
    
    # Сохраняем данные о подарке
    save_user_data(user_id, "gift", {
        'name': gift_info['name'],
        'price': gift_info['price'],
        'gift_id': gift_info['gift_id']
    })
    
    text = (
        f"<tg-emoji emoji-id=\"5380006756594243067\">💎</tg-emoji><b>Подарок: {gift_info['name']}</b>\n\n"
        f"💰 Стоимость: {gift_info['price']}₽\n\n"
        f"Для кого вы приобретаете подарок?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💫 Себе", callback_data="gift_self")],
        [InlineKeyboardButton(text="🎁 Подарить другу", callback_data="gift_friend")],
        [InlineKeyboardButton(text="Назад", callback_data="nft")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ===== ПОДАРОК СЕБЕ =====
@router.callback_query(F.data == "gift_self")
async def gift_self(callback: CallbackQuery):
    user_id = callback.from_user.id
    gift_data = get_user_data(user_id, "gift")
    
    if not gift_data:
        await callback.answer("❌ Сначала выберите подарок", show_alert=True)
        return
    
    username = callback.from_user.username
    if not username:
        username = f"id{user_id}"
    else:
        username = f"@{username}"
    
    text = (
        f"<tg-emoji emoji-id=\"5380006756594243067\">💎</tg-emoji><b>Подарок: {gift_data['name']}</b>\n\n"
        f"💰 Стоимость: {gift_data['price']}₽\n"
        f"👤 Получатель: {username}\n\n"
        f"Выберите способ оплаты:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 СБП", callback_data=f"sbp_gift_self_{gift_data['price']}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="nft")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# ===== ПОДАРОК ДРУГУ =====
@router.callback_query(F.data == "gift_friend")
async def gift_friend(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    gift_data = get_user_data(user_id, "gift")
    
    if not gift_data:
        await callback.answer("❌ Сначала выберите подарок", show_alert=True)
        return
    
    text = (
        f"<tg-emoji emoji-id=\"5380006756594243067\">💎</tg-emoji><b>Подарок: {gift_data['name']}</b>\n\n"
        f"💰 Стоимость: {gift_data['price']}₽\n\n"
        f"👤 Введите @username получателя:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="nft")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state("waiting_for_gift_username")
    await callback.answer()


# ===== ОБРАБОТКА USERNAME ДЛЯ ПОДАРКА =====
@router.message(Form.waiting_for_gift_username)
async def process_gift_username(message: Message, state: FSMContext):
    await delete_user_message(message.from_user.id, message.message_id)
    
    username = message.text.strip()
    if not username:
        error_msg = await message.answer("❌ Пожалуйста, введите username")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)
        return
    
    # Проверяем существование username
    from username_checker import check_username
    
    check_msg = await message.answer("🔍 Проверяю пользователя...")
    result = await check_username(username)
    await delete_user_message(message.from_user.id, check_msg.message_id)
    
    if not result['exists']:
        error_text = f"❌ Пользователь {username} не найден"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="gift_friend")]
        ])
        sent_message = await message.answer(error_text, reply_markup=keyboard)
        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()
        return
    
    if not username.startswith('@'):
        username = f"@{username}"
    
    user_id = message.from_user.id
    gift_data = get_user_data(user_id, "gift")
    
    if not gift_data:
        await message.answer("❌ Ошибка данных")
        await state.clear()
        return
    
    text = (
        f"<tg-emoji emoji-id=\"5380006756594243067\">💎</tg-emoji><b>Подарок: {gift_data['name']}</b>\n\n"
        f"💰 Стоимость: {gift_data['price']}₽\n"
        f"👤 Получатель: {username}\n\n"
        f"Выберите способ оплаты:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 СБП", callback_data=f"sbp_gift_friend_{gift_data['price']}_{username}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="nft")]
    ])
    
    sent_message = await message.answer(text, reply_markup=keyboard)
    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.clear()


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
    # Удаляем сообщение пользователя
    await delete_user_message(message.from_user.id, message.message_id)

    try:
        star_value = int(message.text.strip())

        if star_value < 1 or star_value > 1000000:
            error_msg = await message.answer("❌ Количество должно быть от 50 до 1,000,000")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        # Расчет стоимости
        formulastar = round(star_value * 1.65, 1)

        # Сохраняем данные
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
            [InlineKeyboardButton(text="Купить себе", callback_data="buy_stars_self",
                                  icon_custom_emoji_id=5406604187683270743)],
            [InlineKeyboardButton(text="Подарить другу", callback_data="gift_stars_friend",
                                  icon_custom_emoji_id=5203996991054432397)],
            [InlineKeyboardButton(text="Назад", callback_data="stars")]
        ])

        try:
            sent_message = await message.answer_photo(caption=text, reply_markup=keyboard)
        except:
            sent_message = await message.answer(text, reply_markup=keyboard)

        await save_and_delete_previous(message.from_user.id, sent_message.message_id)
        await state.clear()

    except ValueError:
        error_msg = await message.answer("❌Пожалуйста, введите корректное число")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)


# ===== КНОПКА "КУПИТЬ СЕБЕ" =====
@router.callback_query(F.data == "buy_stars_self")
async def buy_stars_self_callback(callback: CallbackQuery):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    user_id = callback.from_user.id
    stars_data = get_user_data(user_id, "stars")

    if not stars_data:
        await callback.answer("❌Сначала выберите количество звёзд", show_alert=True)
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
        f"<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulastar}₽ \n"
        f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Получатель:</b> {username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_stars_self_{formulastar}",
                              icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="Cryptobot", callback_data=f"crypto_stars_{round(formulastar / 0.97, 1)}",
                              icon_custom_emoji_id=5361914370068613491)],
        [InlineKeyboardButton(text="❌Отмена", callback_data="back_to_stars_choice")]
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
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

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
        sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
    except:
        sent_message = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent_message.message_id)
    await state.set_state(Form.waiting_for_friend_username)
    await callback.answer()


# ===== ВОЗВРАТ К ВЫБОРУ ПОЛУЧАТЕЛЯ =====
@router.callback_query(F.data == "back_to_stars_choice")
async def back_to_stars_choice_callback(callback: CallbackQuery):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    user_id = callback.from_user.id
    stars_data = get_user_data(user_id, "stars")

    if not stars_data:
        await callback.answer("❌ Данные не найдены", show_alert=True)
        return

    star_value = stars_data['star_value']
    formulastar = stars_data['formulastar']
    star_ton = stars_data.get('formulaTON', stars_data.get('price_ton', 0))

    text = (
        f"<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulastar}₽ \n\n"
        f"Для кого вы приобретаете:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить себе", callback_data="buy_stars_self",
                              icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="Подарить другу", callback_data="gift_stars_friend",
                              icon_custom_emoji_id=5203996991054432397)],
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
    star_ton = stars_data.get('formulaTON', stars_data.get('price_ton', 0))

    text = (
        f"<tg-emoji emoji-id=\"5438391541288689158\">⭐️</tg-emoji><b>Telegram Stars</b>\n\n"
        f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {formulastar}₽ \n"
        f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Получатель:</b> {username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_stars_friend_{formulastar}",
                              icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="Cryptobot", callback_data=f"crypto_stars_friend_{round(formulastar / 0.97, 1)}",
                              icon_custom_emoji_id=5361914370068613491)],
        [InlineKeyboardButton(text="❌Отмена", callback_data="back_to_stars_choice")]
    ])

    try:
        sent_message = await message.answer_photo(caption=text, reply_markup=keyboard)
    except:
        sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.clear()


# ===== ВСЁ ДЛЯ TON (ОДНИМ БЛОКОМ) =====

# ===== КОМАНДА /TON =====
@router.message(Command("ton"))
async def ton_cmd(message: Message, state: FSMContext):
    await state.clear()
    global TON_RUB
    TON_RUB = await get_ton_price()

    text = (
        f"<tg-emoji emoji-id=\"5438332129006081114\">💎</tg-emoji><b>TON</b>\n\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Курс к рублю:</b> {round(TON_RUB + 25, 2)}₽\n"
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


# ======ОБРАБОТКА СУММЫ ТОН======
@router.message(Form.waiting_for_ton_amount)
async def process_ton_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await delete_user_message(message.from_user.id, message.message_id)

    try:
        # 🔥 Проверяем, что введено целое число (без точки)
        text = message.text.strip()

        # Проверка: только цифры, никаких точек и запятых
        if not text.isdigit():
            error_msg = await message.answer("❌Введите целое число без дробной части (например: 5, 10, 100)")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        ton_value = int(text)

        if ton_value < 1:
            error_msg = await message.answer("❌Введите целое значение от 1 TON")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        formulaTON = round(ton_value * (TON_RUB + 20), 1)

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
            [InlineKeyboardButton(text="Купить себе", callback_data="buy_ton_self",
                                  icon_custom_emoji_id=5406604187683270743)],
            [InlineKeyboardButton(text="Подарить другу", callback_data="gift_ton_friend",
                                  icon_custom_emoji_id=5203996991054432397)],
            [InlineKeyboardButton(text="Назад", callback_data="ton")]
        ])

        try:
            sent_message = await message.answer_photo(caption=text, reply_markup=keyboard)
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
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    user_id = callback.from_user.id
    data = get_user_data(user_id, "ton_purchase")

    if not data:
        await callback.answer("❌ Сначала выберите сумму", show_alert=True)
        return

    ton_value = data['ton_value']
    formulaTON = data['formulaTON']

    # Получаем username покупателя
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
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_ton_self_{formulaTON}",
                              icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="CryptoBot", callback_data=f"crypto_ton_{formulaTON}",
                              icon_custom_emoji_id=5361914370068613491)],
        [InlineKeyboardButton(text="❌Отмена", callback_data="ton")]
    ])

    try:
        sent = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
    except:
        sent = await callback.message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(user_id, sent.message_id)
    await callback.answer()


# ===== ПОДАРИТЬ ДРУГУ =====
@router.callback_query(F.data == "gift_ton_friend")
async def ton_friend_callback(callback: CallbackQuery, state: FSMContext):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    user_id = callback.from_user.id
    data = get_user_data(user_id, "ton_purchase")

    if not data:
        await callback.answer("❌Сначала выберите сумму", show_alert=True)
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
        sent = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
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

    # Проверка username (Telethon)
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
        [InlineKeyboardButton(text="СБП", callback_data=f"sbp_ton_friend_{formulaTON}",
                              icon_custom_emoji_id=5305413839066525446)],
        [InlineKeyboardButton(text="CryptoBot", callback_data=f"crypto_ton_{formulaTON}",
                              icon_custom_emoji_id=5361914370068613491)],
        [InlineKeyboardButton(text="❌Отмена", callback_data="ton")]
    ])

    try:
        sent = await message.answer_photo(caption=text, reply_markup=keyboard)
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
        photo = FSInputFile("images/premium.jpg")
        sent_message = await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)


# ===== КНОПКИ PREMIUM =====
@router.callback_query(F.data.startswith("premium_"))
async def premium_period_callback(callback: CallbackQuery, state: FSMContext):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    periods = {
        "premium_12": "12 месяцев",
        "premium_6": "6 месяцев",
        "premium_3": "3 месяца"
    }

    prices = {
        "premium_12": 2999,
        "premium_6": 1699,
        "premium_3": 1299
    }

    period = periods.get(callback.data, "3 месяца")
    priceprem = prices.get(callback.data, 1300)

    save_user_data(callback.from_user.id, "premium", {
        'period': period,
        'priceprem': priceprem
    })

    text = (
        f"<tg-emoji emoji-id=\"5402352097045795954\">👑</tg-emoji><b>Telegram Premium</b>\n\n"
        f"<tg-emoji emoji-id=\"5274055917766202507\">🗓</tg-emoji><b>Срок:</b> {period}\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {priceprem}₽\n\n"
        f"Для кого вы приобретаете:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить себе", callback_data="buy_premium_self",
                              icon_custom_emoji_id=5406604187683270743)],
        [InlineKeyboardButton(text="Подарить другу", callback_data="gift_premium_friend",
                              icon_custom_emoji_id=5203996991054432397)],
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
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

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
            [InlineKeyboardButton(text="Подарить другу", callback_data="gift_premium_friend",
                                  icon_custom_emoji_id=5203996991054432397)],
            [InlineKeyboardButton(text="Назад", callback_data="premium")]
        ])

        try:
            sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
        except:
            sent_message = await callback.message.answer(text, reply_markup=keyboard)

    else:
        # У пользователя НЕТ Premium - можно оформлять
        text = (
            f"<tg-emoji emoji-id=\"5402352097045795954\">👑</tg-emoji><b>Telegram Premium</b>\n\n"
            f"<tg-emoji emoji-id=\"5274055917766202507\">🗓</tg-emoji><b>Срок:</b> {period}\n"
            f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {priceprem}₽\n"
            f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Получатель</b>: {username}\n\n"
            f"Выберите способ оплаты:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="СБП", callback_data=f"sbp_premium_self_{priceprem}",
                                  icon_custom_emoji_id=5305413839066525446)],
            [InlineKeyboardButton(text="Cryptobot", callback_data=f"crypto_premium_{round(priceprem / 0.97, 1)}",
                                  icon_custom_emoji_id=5361914370068613491)],
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
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    user_id = callback.from_user.id
    premium_data = get_user_data(user_id, "premium")

    if not premium_data:
        await callback.answer("❌ Сначала выберите период", show_alert=True)
        return

    period = premium_data['period']
    priceprem = premium_data['priceprem']

    text = (
        f"<tg-emoji emoji-id=\"5402352097045795954\">👑</tg-emoji><b>Telegram Premium</b>\n\n"
        f"<tg-emoji emoji-id=\"5274055917766202507\">🗓</tg-emoji><b>Срок:</b> {period}\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {priceprem}₽\n\n"
        f"Введите @username получателя:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="premium")]
    ])

    try:
        sent_message = await callback.message.answer_photo(caption=text, reply_markup=keyboard)
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

            sent_message = await message.answer_photo(caption=text, reply_markup=keyboard)
        except:
            sent_message = await message.answer(text, reply_markup=keyboard)

    else:
        # У пользователя НЕТ Premium - можно оформлять
        text = (
            f"<tg-emoji emoji-id=\"5402352097045795954\">👑</tg-emoji><b>Telegram Premium</b>\n\n"
            f"<tg-emoji emoji-id=\"5274055917766202507\">🗓</tg-emoji><b>Срок:</b> {period}\n"
            f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Стоимость:</b> {priceprem}₽\n"
            f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Получатель:</b> {username}\n\n"
            f"Выберите способ оплаты:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="СБП", callback_data=f"sbp_premium_friend_{priceprem}",
                                  icon_custom_emoji_id=5305413839066525446)],
            [InlineKeyboardButton(text="Cryptobot", callback_data=f"crypto_premium_{round(priceprem / 0.97, 1)}",
                                  icon_custom_emoji_id=5361914370068613491)],
            [InlineKeyboardButton(text="❌Отмена", callback_data="premium")]
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
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return
    await menu_cmd(callback.message)
    await callback.answer()


@router.callback_query(F.data == "stars")
async def stars_btn(callback: CallbackQuery, state: FSMContext):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return
    await stars_cmd(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "ton")
async def ton_btn(callback: CallbackQuery, state: FSMContext):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return
    await ton_cmd(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "premium")
async def premium_btn(callback: CallbackQuery):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return
    await premium_cmd(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("crypto_"))
async def crypto_payment(callback: CallbackQuery):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    user_id = callback.from_user.id
    parts = callback.data.split("_")

    if len(parts) < 3:
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # ✅ ЭТО УЖЕ ЕСТЬ
    ptype = parts[1]  # stars, premium, ton
    amount = float(parts[2])

    # 👇 А ЭТО НУЖНО ДОБАВИТЬ
    stars_data = get_user_data(user_id, "stars")
    premium_data = get_user_data(user_id, "premium")
    ton_data = get_user_data(user_id, "ton_purchase")

    # Дальше определяем описание и комиссию
    if ptype == "stars" and stars_data:
        star_value = stars_data.get('star_value', '?')
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд"
        base_price = round(star_value * 1.65, 1)
        commission = round(amount - base_price, 1)

    elif ptype == "premium" and premium_data:
        period = premium_data.get('period', 'Premium')
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> Telegram Premium на {period}"
        base_prices = {"12 месяцев": 3000, "6 месяцев": 1700, "3 месяца": 1300}
        base_price = base_prices.get(period, amount)
        commission = round(amount - base_price, 1)

    elif ptype == "ton" and ton_data:
        ton_value = ton_data.get('ton_value', '?')
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {ton_value} TON"
        base_price = round(ton_value * TON_RUB, 1)
        commission = round(amount - base_price, 1)

    payload = f"{ptype}_{user_id}_{int(time.time())}"

    # Дальше создаем счет...
    wait_msg = await callback.message.answer("Создаю счет...")

    from username_checker import create_crypto_invoice
    result = await create_crypto_invoice(amount, description, payload)

    await delete_user_message(user_id, wait_msg.message_id)

    if result["success"]:
        # Сохраняем для отслеживания
        if user_id not in user_data:
            user_data[user_id] = {}
        if "pending_invoices" not in user_data[user_id]:
            user_data[user_id]["pending_invoices"] = {}

        user_data[user_id]["pending_invoices"][result["invoice_id"]] = {
            "type": ptype,
            "amount": amount,
            "time": time.time()
        }

        asyncio.create_task(track_payment(user_id, result["invoice_id"], ptype))

        # Отправляем ссылку
        text = (
            f"<tg-emoji emoji-id=\"5361914370068613491\">👛</tg-emoji><b>CryptoBot</b>\n\n"
            f"{description}\n"
            f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Сумма:</b> {round(amount/0.97, 1)}₽ (комиссия {round(commission, 2)}₽)\n"
            f"<tg-emoji emoji-id=\"5274099962655816924\">❗️</tg-emoji><b>Комиссия:</b>3%\n\n"
            f"👇Нажмите кнопку для оплаты:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Оплатить", url=result["pay_url"])],
            [InlineKeyboardButton(text="❌Отмена", callback_data=ptype)]
        ])

        # Отправляем с фото
        try:
            if ptype == "stars":
                sent = await callback.message.answer_photo(caption=text, reply_markup=keyboard,
                                                           parse_mode="HTML")
            elif ptype == "premium":
                sent = await callback.message.answer_photo(caption=text, reply_markup=keyboard,
                                                           parse_mode="HTML")
            elif ptype == "ton":
                sent = await callback.message.answer_photo(caption=text, reply_markup=keyboard,
                                                           parse_mode="HTML")
            else:
                sent = await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        except:
            sent = await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        await save_and_delete_previous(user_id, sent.message_id)
    else:
        # Ошибка
        error_text = f"❌Ошибка: {result.get('error', 'Неизвестная ошибка')}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=" Назад", callback_data=ptype)]
        ])
        sent = await callback.message.answer(error_text, reply_markup=keyboard)
        await save_and_delete_previous(user_id, sent.message_id)

    await callback.answer()


async def track_payment(user_id: int, invoice_id: str, payment_type: str):
    """Автоматически проверяет оплату каждые 10 секунд"""
    from username_checker import check_invoice_status

    for _ in range(36):  # 6 минут
        await asyncio.sleep(10)

        result = await check_invoice_status(invoice_id)

        if result.get("success") and result.get("status") == "paid":
            try:
                await bot.send_message(
                    user_id,
                    f"✅ <b>Оплата подтверждена!</b>\n\nСпасибо за покупку!\n/menu — вернуться в меню",
                    parse_mode="HTML"
                )
                print(f"✅ Платеж {invoice_id} подтвержден")
            except:
                pass
            break

        if result.get("status") in ["expired", "cancelled"]:
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


# ====== SBP =======
@router.callback_query(F.data.startswith("sbp_"))
async def sbp_payment(callback: CallbackQuery):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    user_id = callback.from_user.id
    parts = callback.data.split("_")

    if len(parts) >= 4:
        ptype = parts[1]
        recipient = parts[2]
        amount = float(parts[3])
        print(f"✅ Тип: {ptype}, Получатель: {recipient}, Сумма: {amount}")
    else:
        print(f"❌ Недостаточно частей: {len(parts)}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # 👇 ПОЛУЧАЕМ ДАННЫЕ ИЗ ХРАНИЛИЩА
    stars_data = get_user_data(user_id, "stars")
    premium_data = get_user_data(user_id, "premium")
    ton_data = get_user_data(user_id, "ton_purchase")

    # 👇 ПОЛУЧАЕМ USERNAME
    username = callback.from_user.username
    if not username:
        username = f"id{user_id}"
    else:
        username = f"@{username}"

    # 👇 ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ КУРСА TON
    global TON_RUB

    # 👇 ЗАДАЁМ НАЧАЛЬНЫЕ ЗНАЧЕНИЯ
    description = f"Оплата {amount}₽"
    base_price = amount
    final_amount = amount
    quantity = "1"

    # Определяем описание и разделяем цены для каждого типа товара
    if ptype == "stars" and stars_data:
        star_value = stars_data.get('star_value', 1)
        quantity = str(star_value)
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд"
        base_price = round(star_value * 1.65, 1)
        final_amount = round(base_price / 0.92, 1)

    elif ptype == "gift" and gift_data:
        gift_id = gift_data.get('gift_id')
        gift_name = gift_data.get('name')
        description = f"<tg-emoji emoji-id=\"5380006756594243067\">💎</tg-emoji><b>Подарок: {gift_name}</b>"
        base_price = gift_data.get('price')
        final_amount = round(base_price / 0.92, 1)
        quantity = "1"
    
    # Payload: gift_IDподарка_сумма_получатель
    payload = f"gift_{gift_id}_{round(final_amount, 1)}_{recipient}"

    elif ptype == "premium" and premium_data:
        period = premium_data.get('period', 'Premium')
        priceprem = premium_data.get('priceprem', amount)
        print(f"👑 Premium данные: period={period}, priceprem={priceprem}")
        
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> Telegram Premium на {period}"
        base_prices = {
            "12 месяцев": 2999,
            "6 месяцев": 1699,
            "3 месяца": 1299
        }
        base_price = base_prices.get(period, priceprem)
        final_amount = round(base_price / 0.92, 1)
        quantity = "12" if period == "12 месяцев" else "6" if period == "6 месяцев" else "3"

    elif ptype == "ton" and ton_data:
        ton_value = ton_data.get('ton_value', 1)
        quantity = str(ton_value)
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {ton_value} TON"
        base_price = round(ton_value * (TON_RUB + 30), 1)
        final_amount = round(base_price / 0.92, 1)

    # Формируем payload для вебхука (тип_количество_сумма_получатель)
    payload = f"{ptype}_{quantity}_{round(final_amount, 1)}_{username}"

    wait_msg = await callback.message.answer("Создаю ссылку для оплаты...")

    from username_checker import create_platega_invoice

    # Описание для Platega
    platega_description = f"Спасибо за покупку! Ждем вас снова в SpireShop"

    result = await create_platega_invoice(
        amount_rub=final_amount,
        description=platega_description,
        order_id=payload
    )

    await delete_user_message(user_id, wait_msg.message_id)

    if result["success"]:
        text = (
            f"<tg-emoji emoji-id=\"5305413839066525446\">🏦</tg-emoji><b>Оплата по СБП</b>\n\n"
            f"{description}\n"
            f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Сумма к оплате:</b> {round(final_amount, 1)}₽ (комиссия {round(final_amount - base_price, 1)}₽)\n"
            f"<tg-emoji emoji-id=\"5274099962655816924\">❗️</tg-emoji><b>Комиссия сервиса:</b> 8%\n\n"
            f"👇Нажмите кнопку для оплаты:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить", url=result["pay_url"])],
            [InlineKeyboardButton(text="❌Отмена", callback_data=ptype)]
        ])

        sent = await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await save_and_delete_previous(user_id, sent.message_id)
    else:
        await callback.message.answer(f"❌ Ошибка: {result.get('error')}")

    await callback.answer()
# ===== ХРАНИЛИЩЕ ДЛЯ ВЕБХУКА =====
processed_webhooks = set()

# ===== ВЕБХУК ДЛЯ PLATEGA =====
async def platega_webhook(request):
    try:
        data = await request.json()
        print(f"📩 Platega webhook: {json.dumps(data, indent=2)}")
        
        transaction_id = data.get('transactionId')
        status = data.get('status')
        payload = data.get('payload', '')
        
        # Защита от дубликатов
        if transaction_id in processed_webhooks:
            print(f"⚠️ Дубликат {transaction_id}, игнорируем")
            return web.Response(text="OK", status=200)
        processed_webhooks.add(transaction_id)
        
        if status == 'SUCCESS' and payload:
            parts = payload.split('_')
            print(f"📦 Payload части: {parts}")
            
            # Формат: тип_данные_сумма_получатель
            if len(parts) >= 3:
                ptype = parts[0]        # stars, premium, ton, gift
                quantity = parts[1]      # количество или gift_id
                amount = float(parts[2])  # сумма
                recipient = parts[3] if len(parts) > 3 else None
                
                # Получаем ID пользователя из payload или из данных
                user_id = None
                if recipient:
                    # Пытаемся найти пользователя по username
                    try:
                        user = await bot.get_chat(recipient)
                        user_id = user.id
                    except:
                        # Если не нашли — возможно ID в payload
                        pass
                
                # ===== ОБРАБОТКА ПОДАРКА =====
                if ptype == "gift":
                    gift_id = int(quantity)
                    
                    # Отправляем подарок через Telethon
                    from username_checker import send_telegram_gift
                    
                    gift_result = await send_telegram_gift(
                        receiver_username=recipient.replace('@', ''),
                        gift_id=gift_id,
                        text="Поздравляю с подарком! 🎁"
                    )
                    
                    if gift_result["success"]:
                        # Уведомление покупателю (если знаем user_id)
                        if user_id:
                            await bot.send_message(
                                user_id,
                                f"✅ Подарок отправлен {recipient}!\nСпасибо за покупку!\n/menu — вернуться в меню",
                                parse_mode="HTML"
                            )
                        
                        # Уведомление админу
                        admin_text = (
                            f"🎁 <b>ПОДАРОК ОТПРАВЛЕН</b>\n\n"
                            f"👤 <b>Получатель:</b> {recipient}\n"
                            f"🆔 <b>ID подарка:</b> {gift_id}\n"
                            f"💵 <b>Сумма:</b> {amount}₽\n"
                            f"🧾 <b>Транзакция:</b> <code>{transaction_id}</code>\n"
                            f"⏱ <b>Время:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
                        print(f"✅ Подарок отправлен {recipient}")
                    else:
                        # Ошибка отправки подарка
                        error_text = f"❌ Ошибка отправки подарка: {gift_result.get('error')}"
                        if user_id:
                            await bot.send_message(user_id, error_text)
                        print(f"❌ Ошибка: {gift_result.get('error')}")
                
                # ===== ОБРАБОТКА ЗВЁЗД, PREMIUM, TON =====
                else:
                    # Название товара на русском
                    product_names = {
                        "stars": "Звёзды",
                        "premium": "Premium",
                        "ton": "TON"
                    }
                    product_name = product_names.get(ptype, ptype.upper())
                    
                    # Уведомление пользователю
                    if user_id:
                        user_text = (
                            f"✅ <b>Оплата подтверждена!</b>\n\n"
                            f"📦 <b>Товар:</b> {product_name}\n"
                            f"🔢 <b>Количество:</b> {quantity}\n"
                            f"💵 <b>Сумма:</b> {amount}₽\n\n"
                            f"Спасибо за покупку!\n/menu — вернуться в меню"
                        )
                        await bot.send_message(user_id, user_text, parse_mode="HTML")
                    
                    # Уведомление админу
                    admin_text = (
                        f"💰 <b>НОВЫЙ ПЛАТЁЖ</b>\n\n"
                        f"👤 <b>Пользователь:</b> {recipient or 'неизвестно'}\n"
                        f"🆔 <b>ID:</b> <code>{user_id or 'неизвестно'}</code>\n"
                        f"📦 <b>Товар:</b> {product_name}\n"
                        f"🔢 <b>Количество:</b> {quantity}\n"
                        f"💵 <b>Сумма:</b> {amount}₽\n"
                        f"🧾 <b>Транзакция:</b> <code>{transaction_id}</code>\n"
                        f"⏱ <b>Время:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
                    print(f"✅ Платёж подтверждён: {ptype} {quantity} за {amount}₽")
        
        return web.Response(text="OK", status=200)
        
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")
        import traceback
        traceback.print_exc()
        return web.Response(text="Error", status=500)

# ===== АДМИН-ПАНЕЛЬ =====
@router.message(Command("admin"))
async def admin_panel(message: Message):
    # Проверка что это админ
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return

    text = (
        f"<b> АДМИН-ПАНЕЛЬ</b>\n\n"
        f"Выберите действие:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="Изменить цены", callback_data="admin_prices")],
        [InlineKeyboardButton(text="Закрыть", callback_data="menu")]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ===== ОБРАБОТЧИКИ АДМИНКИ =====
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"<b>РАССЫЛКА</b>\n\n"
        f"Всего пользователей: {len(user_ids)}\n\n"
        f"Введите текст для рассылки (можно использовать HTML):"
    )
    
    await state.set_state("waiting_broadcast_text")
    await callback.answer()

@router.message(StateFilter("waiting_broadcast_text"))
async def process_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    text = message.html_text
    
    status_msg = await message.answer(f"📢 Начинаю рассылку {len(user_ids)} пользователям...")
    
    sent = 0
    failed = 0
    
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            sent += 1
            if sent % 10 == 0:
                await status_msg.edit_text(f"📢 Отправлено: {sent}/{len(user_ids)}")
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            print(f"❌ Ошибка отправки {user_id}: {e}")
    
    await status_msg.edit_text(
        f"<b>Рассылка завершена!</b>\n\n"
        f"Отправлено: {sent}\n"
        f" Не удалось: {failed}\n"
        f" Всего: {len(user_ids)}",
        parse_mode="HTML"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back")]
    ])
    await message.answer("Что дальше?", reply_markup=keyboard)
    await state.clear()


@router.message(StateFilter("waiting_price_change"))
async def change_price(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            raise ValueError
        
        key = parts[0]
        value = float(parts[1])
        
        if key in PRICES:
            PRICES[key] = value
            await message.answer(f"✅ Цена <b>{key}</b> изменена на {value}₽", parse_mode="HTML")
            
            # Обновляем глобальные переменные, которые используют цены
            global formulastar, priceprem, TON_RUB
            # Здесь можно обновить и другие переменные, если нужно
            
        else:
            await message.answer(f"❌ Неизвестный товар: {key}\nДоступно: {', '.join(PRICES.keys())}")
            
    except:
        await message.answer("❌ Неверный формат\nПример: <code>stars 1.7</code>", parse_mode="HTML")
    
    await state.clear()



@router.callback_query(F.data == "admin_prices")
async def admin_prices(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = (
        f"<b>ТЕКУЩИЕ ЦЕНЫ</b>\n\n"
        f"<b>Stars:</b> {PRICES['stars']}₽ за звезду\n"
        f"<b>Premium 12 мес:</b> {PRICES['premium_12']}₽\n"
        f"<b>Premium 6 мес:</b> {PRICES['premium_6']}₽\n"
        f"<b>Premium 3 мес:</b> {PRICES['premium_3']}₽\n"
        f"<b>TON наценка:</b> +{PRICES['ton_markup']}₽\n\n"
        f" <b>Как изменить:</b>\n"
        f"<code>stars 1.7</code> — изменить цену звезды\n"
        f"<code>premium_12 3000</code> — изменить Premium 12 мес\n"
        f"<code>ton_markup 25</code> — изменить наценку TON"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state("waiting_price_change")
    await callback.answer()

@router.callback_query(F.data == "admin_panel_back")
async def admin_panel_back(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    text = (
        f"<b>👑 АДМИН-ПАНЕЛЬ</b>\n\n"
        f"👥 <b>Всего пользователей:</b> {len(user_ids)}\n"
        f"🆔 <b>Ваш ID:</b> <code>{ADMIN_ID}</code>\n\n"
        f"Выберите действие:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📦 Последние заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="⚙️ Изменить цены", callback_data="admin_prices")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="menu")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# ===== ЗАПУСК =====
async def main():

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
