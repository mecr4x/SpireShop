import asyncio
import sys
import time

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiohttp
from aiogram import Bot, Dispatcher, Router, F  # 👈 Router отсюда!
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command, StateFilter, state
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
# Создаём роутер
router = Router()

# ===== ДЛЯ АДМИНКИ =====
user_ids = set()  # множество для хранения ID всех пользователей
admin_commands = {}  # для хранения временных данных

# Сохраняем пользователя при любом сообщении
@router.message()
async def save_user_on_message(message: Message):
    user_ids.add(message.from_user.id)
    # Пропускаем сообщение дальше (не блокируем другие хендлеры)
    await asyncio.sleep(0)  # просто даем шанс другим хендлерам

# Сохраняем пользователя при любом callback
@router.callback_query()
async def save_user_on_callback(callback: CallbackQuery):
    user_ids.add(callback.from_user.id)
    await asyncio.sleep(0)
# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8236812443:AAHgQEWDwQMDAHhv8sIRxhKqmsToX9Rn85c"
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
    waiting_for_steam_login = State()
    waiting_for_steam_amount = State()
    waiting_for_premium_steam = State()
class AdminStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_text = State()
    waiting_for_button = State()
    waiting_for_callback = State()



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
    user_ids.add(message.from_user.id)
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
    user_ids.add(callback.from_user.id)
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
        [InlineKeyboardButton(text="Купить звёзды", callback_data="stars", icon_custom_emoji_id=5438391541288689158)],
        [InlineKeyboardButton(text="Пополнить TON", callback_data="ton", icon_custom_emoji_id=5438332129006081114)],
        [InlineKeyboardButton(text="Купить Premium", callback_data="premium",
                              icon_custom_emoji_id=5402352097045795954)],
        [InlineKeyboardButton(text="Пополнить Steam", callback_data="steam",icon_custom_emoji_id=5373144051690258848)],
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

@router.message(Command("steam"))
async def steam_cmd(message: Message, state: FSMContext):
    await state.clear()
    user_ids.add(message.from_user.id)
    text = (
        "<tg-emoji emoji-id=\"5373144051690258848\">📱</tg-emoji><b>Пополнение Steam</b>\n\n"
        "<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji><b>Примечание: обязательно прочтите перед пополнением</b>\n"
        "<blockquote>"
        "<tg-emoji emoji-id=\"6021443182900812386\">🌎</tg-emoji><b>Регион аккаунта</b>\n\n"
        "Страной Вашего аккаунта должна быть одна из стран СНГ (Казахстан, Узбекистан, Кыргызстан, Россия и т.д).\n\n"
        "❗️Кроме Крыма, Луганска и Донецка — в данных регионах пополнение недоступно.\n\n"
        "Для аккаунтов со странами Китай, Турция и другими, не входящими в СНГ странам — пополнение недоступно.\n\n"
        "<tg-emoji emoji-id=\"5436113877181941026\">❓</tg-emoji><b>Что такое логин?</b>\n\n"
        "Логин — это то что вы вводите при авторизации, у каждого пользователя он уникальный, а никнейм вы можете менять по своему усмотрению."
        "<b>Не перепутайте ваш логин и никнейм.</b>"
        "</blockquote>\n\n"
        "<b>Введите логин Steam (тот, что используете при входе):</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

    try:
        photo = FSInputFile("images/steam.jpg")
        sent_message = await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
    except:
        sent_message = await message.answer(text, reply_markup=keyboard)

    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.set_state(Form.waiting_for_steam_login)


@router.message(Form.waiting_for_steam_login)
async def process_steam_login(message: Message, state: FSMContext):
    await delete_user_message(message.from_user.id, message.message_id)

    steam_login = message.text.strip()

    # Простая проверка на пустоту
    if not steam_login:
        error_msg = await message.answer("❌ Пожалуйста, введите логин Steam")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)
        return

    # Проверка через парсинг
    check_msg = await message.answer("🔍 Проверяю логин в Steam...")

    login_exists = await check_steam_login_exists(steam_login)

    await delete_user_message(message.from_user.id, check_msg.message_id)

    if not login_exists:
        error_msg = await message.answer(
            "❌ Логин не найден в Steam\n\n"
            "Проверьте правильность ввода.\n"
            "Логин — это то, что вы вводите при входе в Steam, а не никнейм.\n\n"
            "Попробуйте еще раз:"
        )
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(3)
        await delete_user_message(message.from_user.id, error_msg.message_id)
        return

    # Логин найден - сохраняем
    save_user_data(message.from_user.id, "steam_login", steam_login)

    # Вопрос про сумму пополнения
    text = (
        f"<tg-emoji emoji-id=\"5373144051690258848\">📱</tg-emoji><b>Пополнение Steam</b>\n\n"
        f"<b>Логин:</b> <code>{steam_login}</code>\n\n"
        f"Введите сумму пополнения в рублях (от 100 до 5000):"
    )

    sent_message = await message.answer(text, parse_mode="HTML")
    await save_and_delete_previous(message.from_user.id, sent_message.message_id)
    await state.set_state(Form.waiting_for_steam_amount)


@router.message(Form.waiting_for_steam_amount)
async def process_steam_amount(message: Message, state: FSMContext):
    await delete_user_message(message.from_user.id, message.message_id)

    try:
        amount = int(message.text.strip())

        if amount < 100 or amount > 5000:
            error_msg = await message.answer("❌ Сумма должна быть от 100 до 5000 рублей")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        user_id = message.from_user.id
        steam_login = get_user_data(user_id, "steam_login")

        save_user_data(user_id, "steam", {
            "steam_amount": amount,
            "steam_login": steam_login
        })

        text = (
            f"<tg-emoji emoji-id=\"5373144051690258848\">📱</tg-emoji><b>Пополнение Steam</b>\n\n"
            f"<b>Логин:</b> <code>{steam_login}</code>\n"
            f"<b>Сумма пополнения:</b> {amount}₽\n"
            f"<b>Сумма к оплате: {amount*1.05}₽</b>\n"
            f"<tg-emoji emoji-id=\"5447644880824181073\">⚠️</tg-emoji><b>Примечание:</b>\n"
            f"<blockquote>"
            f"Из-за двойной конвертации (из рублей в доллары, из долларов в валюту аккаунта) до 10% от суммы платежа уйдёт на обмен валют.</blockquote>\n\n"
            f"<b>Выберите способ оплаты:</b>"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="СБП", callback_data=f"sbp_steam_self_{amount}", icon_custom_emoji_id=5305413839066525446)],
            [InlineKeyboardButton(text="CryptoBot", callback_data=f"crypto_steam_{round(amount / 0.97, 1)}", icon_custom_emoji_id=5361914370068613491)],
            [InlineKeyboardButton(text="❌Отмена", callback_data="menu")]
        ])

        sent_message = await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await save_and_delete_previous(user_id, sent_message.message_id)
        await state.clear()

    except ValueError:
        error_msg = await message.answer("❌ Введите число")
        await save_and_delete_previous(message.from_user.id, error_msg.message_id)
        await asyncio.sleep(2)
        await delete_user_message(message.from_user.id, error_msg.message_id)


# ===== ФУНКЦИЯ ПРОВЕРКИ STEAM ЛОГИНА ЧЕРЕЗ ПАРСИНГ =====
async def check_steam_login_exists(login: str) -> bool:
    """Проверяет существует ли логин в Steam через парсинг"""
    try:
        import aiohttp
        url = f"https://steamcommunity.com/id/{login}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as resp:
                html = await resp.text()
                return 'actual_persona_name' in html or 'persona_name' in html
    except:
        return False




# ===== КОМАНДА /STARS =====
@router.message(Command("stars"))
async def stars_cmd(message: Message, state: FSMContext):
    await state.clear()
    user_ids.add(message.from_user.id)

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

        if star_value < 50 or star_value > 1000000:
            error_msg = await message.answer("❌ Количество должно быть от 50 до 1,000,000")
            await save_and_delete_previous(message.from_user.id, error_msg.message_id)
            await asyncio.sleep(2)
            await delete_user_message(message.from_user.id, error_msg.message_id)
            return

        # Расчет стоимости
        formulastar = round(star_value * 1.5, 1)

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

# ===== КОМАНДА /TON =====
@router.message(Command("ton"))
async def ton_cmd(message: Message, state: FSMContext):
    await state.clear()
    user_ids.add(message.from_user.id)
    global TON_RUB
    TON_RUB = await get_ton_price()

    text = (
        f"<tg-emoji emoji-id=\"5438332129006081114\">💎</tg-emoji><b>TON</b>\n\n"
        f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Курс к рублю:</b> {round(TON_RUB + 20, 2)}₽\n"
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
    user_ids.add(message.from_user.id)
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
        "premium_12": 2800,
        "premium_6": 1500,
        "premium_3": 1200
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

@router.callback_query(F.data == "steam")
async def steam_btn(callback: CallbackQuery, state: FSMContext):
    if not await require_subscription_callback(callback):
        return
    await steam_cmd(callback.message, state)
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
        base_price = round(star_value * 1.5, 1)
        commission = round(amount - base_price, 1)

    elif ptype == "premium" and premium_data:
        period = premium_data.get('period', 'Premium')
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> Telegram Premium на {period}"
        base_prices = {"12 месяцев": 2800, "6 месяцев": 1500, "3 месяца": 1200}
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
            f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Сумма:</b> {round(amount, 1)}₽ (комиссия {round(commission, 2)}₽)\n"
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
    steam_data = get_user_data(user_id, "steam")

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

    # Определяем описание и разделяем цены для каждого типа товара
    if ptype == "stars" and stars_data:
        star_value = stars_data.get('star_value', '?')
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {star_value} звёзд"
        base_price = round(star_value * 1.5, 1)
        final_amount = round(base_price / 0.92, 1)

    elif ptype == "premium" and premium_data:
        period = premium_data.get('period', 'Premium')
        priceprem = premium_data.get('priceprem', amount)
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> Telegram Premium на {period}"
        base_prices = {
            "12 месяцев": 2799,
            "6 месяцев": 1499,
            "3 месяца": 1199
        }
        base_price = base_prices.get(period, priceprem)
        final_amount = round(base_price / 0.92, 1)

    elif ptype == "ton" and ton_data:
        ton_value = ton_data.get('ton_value', '?')
        description = f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> {ton_value} TON"
        base_price = round(ton_value * (TON_RUB + 20), 1)
        final_amount = round(base_price / 0.92, 1)

    elif ptype == "steam" and steam_data:
        steam_amount = steam_data.get('steam_amount', amount)
        steam_login = steam_data.get('steam_login', '?')
        description = (f"<tg-emoji emoji-id=\"5954135079662916434\">⭐️</tg-emoji><b>Вы выбрали:</b> Пополнение Steam на {steam_amount}₽\n"
                       f"<tg-emoji emoji-id=\"5255975823436973213\">🎁</tg-emoji><b>Логин:</b> <code>{steam_login}</code>")
        base_price = float(steam_amount * 1.05)
        final_amount = round(base_price / 0.92, 1)

    else:
        await callback.answer("❌ Ошибка: данные не найдены", show_alert=True)
        return

    order_id = f"{ptype}_{user_id}_{int(time.time())}"

    wait_msg = await callback.message.answer("Создаю ссылку для оплаты...")

    from username_checker import create_platega_invoice

    platega_description = f"{ptype.upper()} {round(final_amount, 1)}₽"

    result = await create_platega_invoice(
        amount_rub=final_amount,
        description=platega_description,
        order_id=order_id
    )

    await delete_user_message(user_id, wait_msg.message_id)

    if result["success"]:
        text = (
            f"<tg-emoji emoji-id=\"5305413839066525446\">🏦</tg-emoji><b>Оплата по СБП</b>\n\n"
            f"{description}\n"
            f"<tg-emoji emoji-id=\"5224257782013769471\">💰</tg-emoji><b>Сумма к оплате:</b> {round(final_amount, 1)}₽ (комиссия {round(final_amount - base_price, 1)}₽)\n"
            f"<tg-emoji emoji-id=\"5274099962655816924\">❗️</tg-emoji><b>Комиссия сервиса:</b> 8%\n\n"
            f"👇Нажмите кнопку для оплаты, а после подтвердите оплату, нажав на \"<tg-emoji emoji-id=\"5206607081334906820\">✔️</tg-emoji>Оплатил\""
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить", url=result["pay_url"])],
            [InlineKeyboardButton(text="Оплатил", callback_data=f"paid_{ptype}_{final_amount}_{username}",
                                  icon_custom_emoji_id=5206607081334906820)],
            [InlineKeyboardButton(text="❌Отмена", callback_data=ptype)]
        ])

        sent = await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        await save_and_delete_previous(user_id, sent.message_id)
    else:
        await callback.message.answer(f"❌ Ошибка: {result.get('error')}")

    await callback.answer()

# ===== КНОПКА "Я ОПЛАТИЛ" =====
@router.callback_query(F.data.startswith("paid_"))
async def paid_callback(callback: CallbackQuery):
    # 👇 ПРОВЕРКА ПОДПИСКИ
    if not await require_subscription_callback(callback):
        return

    user_id = callback.from_user.id
    parts = callback.data.split("_")

    if len(parts) >= 4:  # формат: paid_тип_сумма_получатель
        ptype = parts[1]  # stars, premium, ton, steam
        amount = parts[2]  # сумма
        recipient = parts[3]  # получатель (@username или id)

        await delete_user_message(user_id, callback.message.message_id)

        # Название товара на русском
        product_names = {
            "stars": "Звёзды",
            "premium": "Premium",
            "ton": "TON",
            "steam": "Steam"
        }
        product_name = product_names.get(ptype, ptype.upper())

        # Формируем текст заказа в зависимости от типа
        if ptype == "steam":
            # Для Steam получаем логин из сохраненных данных
            steam_data = get_user_data(user_id, "steam")
            steam_login = steam_data.get('steam_login', 'Не указан') if steam_data else 'Не указан'
            steam_amount = steam_data.get('steam_amount', amount) if steam_data else amount

            order_text = (
                f"💰 <b>НОВЫЙ ЗАКАЗ</b>\n\n"
                f"🎮 <b>Логин Steam:</b> <code>{steam_login}</code>\n"
                f"💰 <b>Сумма пополнения:</b> {steam_amount}₽\n"
                f"👤 <b>Покупатель:</b> {recipient}\n"
                f"📦 <b>Товар:</b> {product_name}\n"
                f"⏱ <b>Время оплаты:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            order_text = (
                f"💰 <b>НОВЫЙ ЗАКАЗ</b>\n\n"
                f"🎁 <b>Получатель:</b> {recipient}\n"
                f"📦 <b>Товар:</b> {product_name}\n"
                f"💵 <b>Сумма:</b> {amount}₽\n"
                f"⏱ <b>Время оплаты:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # 👇 ОТПРАВЛЯЕМ ТЕБЕ В ЛИЧКУ
        await callback.bot.send_message(
            chat_id=ADMIN_ID,
            text=order_text,
            parse_mode="HTML"
        )

        # Благодарность покупателю
        await callback.message.answer(
            f"<b>Спасибо за покупку!</b>\n\n"
            f"Ваш заказ принят и передан администратору.\n"
            f"Ждем вас снова в SpireShop<tg-emoji emoji-id=\"5368469082867769478\">😘</tg-emoji>"
        )

        await callback.answer("✅ Заказ отправлен")
    else:
        await callback.answer("❌ Ошибка данных", show_alert=True)


# ===== АДМИН-ПАНЕЛЬ (РАБОЧАЯ) =====
@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Доступ запрещен")
        return

    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать рассылку", callback_data="create_broadcast")],
        [InlineKeyboardButton(text="Статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="Закрыть", callback_data="close_panel")]
    ])

    await message.answer(
        f"Админ панель\n\nПользователей: {len(user_ids)}",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "create_broadcast")
async def create_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен")
        return

    await callback.message.edit_text(
        "ШАГ 1: ОТПРАВЬТЕ ФОТО\n\nДля отмены: /cancel"
    )
    await state.set_state(AdminStates.waiting_for_photo)
    await callback.answer()


@router.message(AdminStates.waiting_for_photo, F.photo)
async def get_photo(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return

    photo = message.photo[-1]
    await state.update_data(photo_id=photo.file_id)

    await message.answer(
        "ШАГ 2: ВВЕДИТЕ ТЕКСТ\n\nМожно использовать HTML: <b>жирный</b>, <i>курсив</i>",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_text)


@router.message(AdminStates.waiting_for_photo)
async def photo_error(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Ошибка: отправьте фото")


@router.message(AdminStates.waiting_for_text)
async def get_text(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return

    text = message.html_text if message.html_text else message.text
    await state.update_data(broadcast_text=text)

    await message.answer(
        "ШАГ 3: ВВЕДИТЕ ТЕКСТ КНОПКИ\n\nПример: Главное меню"
    )
    await state.set_state(AdminStates.waiting_for_button)


@router.message(AdminStates.waiting_for_button)
async def get_button(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return

    button_text = message.text.strip()
    if not button_text:
        await message.answer("Введите текст кнопки")
        return

    await state.update_data(button_text=button_text)

    await message.answer(
        "ШАГ 4: ВВЕДИТЕ CALLBACK_DATA\n\n"
        "Варианты:\n"
        "menu - главное меню\n"
        "stars - купить звезды\n"
        "ton - купить TON\n"
        "premium - купить Premium"
    )
    await state.set_state(AdminStates.waiting_for_callback)


@router.message(AdminStates.waiting_for_callback)
async def get_callback(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await state.clear()
        return

    callback_data = message.text.strip()
    await state.update_data(callback_data=callback_data)

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    button_text = data.get("button_text")
    photo_id = data.get("photo_id")

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text, callback_data=callback_data)]
    ])

    # Предпросмотр
    await message.answer("ПРЕДПРОСМОТР:")

    try:
        await message.answer_photo(
            photo=photo_id,
            caption=broadcast_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except:
        clean_text = broadcast_text.replace('<', '').replace('>', '')
        await message.answer_photo(
            photo=photo_id,
            caption=clean_text,
            reply_markup=keyboard
        )

    # Сохраняем keyboard в state
    await state.update_data(keyboard=keyboard)

    # Кнопки подтверждения
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ОТПРАВИТЬ", callback_data="confirm_send")],
        [InlineKeyboardButton(text="ОТМЕНА", callback_data="cancel_broadcast")]
    ])

    await message.answer(
        f"ПОЛУЧАТЕЛЕЙ: {len(user_ids)}\n\nОтправить?",
        reply_markup=confirm_keyboard
    )


@router.callback_query(F.data == "confirm_send")
async def confirm_send(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен")
        return

    await callback.answer("Отправка...")

    # Получаем данные из state
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    keyboard = data.get("keyboard")
    photo_id = data.get("photo_id")

    # Проверяем данные
    if not broadcast_text:
        await callback.message.edit_text("Ошибка: нет текста")
        return
    if not keyboard:
        await callback.message.edit_text("Ошибка: нет кнопки")
        return
    if not photo_id:
        await callback.message.edit_text("Ошибка: нет фото")
        return

    if len(user_ids) == 0:
        await callback.message.edit_text("Ошибка: нет пользователей")
        return

    # Статусное сообщение
    status_msg = await callback.message.edit_text(
        f"Отправка 0/{len(user_ids)}"
    )

    sent = 0
    failed = 0
    user_list = list(user_ids)

    for i, user_id in enumerate(user_list, 1):
        try:
            # Отправляем фото с клавиатурой
            await callback.bot.send_photo(
                chat_id=user_id,
                photo=photo_id,
                caption=broadcast_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            sent += 1

        except Exception as e:
            error = str(e)

            # Если ошибка в HTML, пробуем без HTML
            if "parse" in error.lower() or "entities" in error.lower():
                try:
                    clean_text = broadcast_text.replace('<', '').replace('>', '')
                    await callback.bot.send_photo(
                        chat_id=user_id,
                        photo=photo_id,
                        caption=clean_text,
                        reply_markup=keyboard
                    )
                    sent += 1
                except:
                    failed += 1
            else:
                failed += 1

        # Обновляем статус каждые 5 сообщений
        if i % 5 == 0 or i == len(user_list):
            await status_msg.edit_text(
                f"Отправлено: {sent}/{len(user_list)}\nОшибок: {failed}"
            )

        await asyncio.sleep(0.05)

    # Финальный отчет
    await status_msg.edit_text(
        f"ГОТОВО!\n\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {failed}\n"
        f"Всего: {len(user_list)}"
    )

    # Кнопка назад
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад в админку", callback_data="back_to_admin")]
    ])
    await callback.message.answer("Выберите действие", reply_markup=back_keyboard)

    await state.clear()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    await state.clear()
    await callback.message.edit_text("Рассылка отменена")

    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад в админку", callback_data="back_to_admin")]
    ])
    await callback.message.answer("Выберите действие", reply_markup=back_keyboard)
    await callback.answer()


@router.callback_query(F.data == "show_stats")
async def show_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="back_to_admin")]
    ])

    await callback.message.edit_text(
        f"СТАТИСТИКА\n\n"
        f"Пользователей: {len(user_ids)}\n"
        f"Заказов: {len(user_data)}",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    await state.clear()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать рассылку", callback_data="create_broadcast")],
        [InlineKeyboardButton(text="Статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="Закрыть", callback_data="close_panel")]
    ])

    await callback.message.edit_text(
        f"Админ панель\n\nПользователей: {len(user_ids)}",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "close_panel")
async def close_panel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    await state.clear()
    await callback.message.delete()
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("Действие отменено")
    else:
        await message.answer("Нет активных действий")


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
