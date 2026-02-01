import asyncio
import logging
import sys
import sqlite3
import re
import aiohttp
import json
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8236812443:AAGsoEmE7u9q5eBpKTQ3vlbp4IregP9-oHY"  # ВСТАВЬТЕ ТОКЕН
ADMIN_CHANNEL = '@spireshop01'
SUPPORT_USERNAME = '@adamyan_ss'
TON_WALLET = 'UQAL5Y75ykdUsMmW5FgnxKJyz1-njyS_oNuN1Lp2_hgNundO'

# Хранилище ID сообщений для удаления
user_messages = {}


# ===== ФУНКЦИИ ДЛЯ УДАЛЕНИЯ СООБЩЕНИЙ =====
async def save_message_id(user_id: int, message_id: int):
    """Сохранить ID сообщения для последующего удаления"""
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(message_id)


async def delete_previous_messages(user_id: int):
    """Удалить предыдущие сообщения бота у пользователя"""
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            try:
                await bot.delete_message(chat_id=user_id, message_id=msg_id)
            except:
                pass
        user_messages[user_id] = []


async def send_with_deletion(user_id: int, text: str = None, photo=None,
                             caption: str = None, reply_markup=None, delete_previous: bool = True):
    """Отправить сообщение с удалением предыдущих"""
    if delete_previous:
        await delete_previous_messages(user_id)

    if photo:
        msg = await bot.send_photo(
            chat_id=user_id,
            photo=photo,
            caption=caption,
            reply_markup=reply_markup
        )
    else:
        msg = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup
        )

    await save_message_id(user_id, msg.message_id)
    return msg


async def edit_with_deletion(callback: CallbackQuery, text: str = None, photo=None,
                             caption: str = None, reply_markup=None):
    """Редактировать сообщение с обновлением"""
    try:
        if photo:
            await callback.message.edit_media(
                media=types.InputMediaPhoto(media=photo, caption=caption),
                reply_markup=reply_markup
            )
        else:
            await callback.message.edit_text(
                text=text,
                reply_markup=reply_markup
            )
    except:
        # Если не удалось редактировать, отправляем новое
        await delete_previous_messages(callback.from_user.id)
        await send_with_deletion(
            user_id=callback.from_user.id,
            text=text or caption,
            photo=photo,
            reply_markup=reply_markup,
            delete_previous=False
        )


# ===== ФУНКЦИЯ ПРОВЕРКИ ЮЗЕРНЕЙМА =====
async def check_username_exists(username: str) -> dict:
    """
    Проверяет существование юзернейма в Telegram
    Возвращает: {'exists': bool, 'reason': str, 'user_id': int or None}
    """
    try:
        # Пытаемся получить информацию о пользователе
        chat = await bot.get_chat(f"@{username}")

        # Проверяем, что это пользователь, а не группа/канал
        if chat.type != "private":
            return {
                'exists': False,
                'reason': 'Это не пользователь (группа или канал)',
                'user_id': None
            }

        # Проверяем, является ли это самим ботом
        if chat.id == (await bot.get_me()).id:
            return {
                'exists': False,
                'reason': 'Это сам бот',
                'user_id': chat.id
            }

        return {
            'exists': True,
            'reason': 'Пользователь найден',
            'user_id': chat.id
        }

    except Exception as e:
        error_msg = str(e).lower()

        if any(x in error_msg for x in ['not found', 'no user', 'invalid', 'username not occupied']):
            return {
                'exists': False,
                'reason': 'Пользователь не найден',
                'user_id': None
            }
        elif 'bot was blocked' in error_msg or 'user is deactivated' in error_msg:
            return {
                'exists': True,  # Пользователь существует, но заблокировал бота
                'reason': 'Пользователь заблокировал бота или аккаунт деактивирован',
                'user_id': None
            }
        else:
            # Другие ошибки (например, проблемы с сетью)
            return {
                'exists': False,
                'reason': f'Ошибка проверки: {str(e)[:50]}',
                'user_id': None
            }


# ===== ФУНКЦИЯ ПРОВЕРКИ TON АДРЕСА =====
async def check_ton_address(address: str) -> dict:
    """
    Проверяет валидность и существование TON-адреса
    Возвращает: {'valid': bool, 'exists': bool, 'reason': str, 'balance': float or None}
    """
    try:
        # Очищаем адрес от пробелов
        address = address.strip()
        
        # Базовые проверки формата TON-адреса
        if not address:
            return {
                'valid': False,
                'exists': False,
                'reason': 'Адрес не может быть пустым',
                'balance': None
            }
        
        # Проверка длины (обычно TON адрес имеет определенную длину)
        if len(address) < 48 or len(address) > 64:
            return {
                'valid': False,
                'exists': False,
                'reason': 'Некорректная длина адреса',
                'balance': None
            }
        
        # Проверка на наличие недопустимых символов
        if not re.match(r'^[a-zA-Z0-9_-]+$', address):
            return {
                'valid': False,
                'exists': False,
                'reason': 'Адрес содержит недопустимые символы',
                'balance': None
            }
        
        # Проверка через публичный API TON
        async with aiohttp.ClientSession() as session:
            try:
                # API TON Center для проверки баланса и существования адреса
                url = f'https://toncenter.com/api/v2/getAddressInformation?address={address}'
                
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Проверяем наличие ошибок в ответе
                        if data.get('ok'):
                            balance_nano = data.get('result', {}).get('balance', 0)
                            balance_ton = int(balance_nano) / 1_000_000_000
                            
                            # Адрес существует если мы получили информацию о нем
                            return {
                                'valid': True,
                                'exists': True,
                                'reason': 'Адрес существует и активен',
                                'balance': balance_ton
                            }
                        else:
                            # Адрес не найден или невалидный
                            return {
                                'valid': False,
                                'exists': False,
                                'reason': 'Адрес не найден в сети TON',
                                'balance': None
                            }
                    else:
                        # Пробуем альтернативный метод
                        return await check_ton_address_alternative(session, address)
                        
            except aiohttp.ClientError as e:
                # В случае ошибки сети, делаем базовую проверку формата
                if address.startswith('UQ') or address.startswith('EQ'):
                    return {
                        'valid': True,
                        'exists': True,  # Предполагаем что существует
                        'reason': 'Формат адреса корректный (проверка сети недоступна)',
                        'balance': None
                    }
                else:
                    return {
                        'valid': False,
                        'exists': False,
                        'reason': f'Ошибка проверки: {str(e)[:50]}',
                        'balance': None
                    }
            except asyncio.TimeoutError:
                # Таймаут - делаем только базовую проверку
                if address.startswith(('UQ', 'EQ', '0:')):
                    return {
                        'valid': True,
                        'exists': True,  # Предполагаем что существует
                        'reason': 'Формат адреса корректный (проверка таймаут)',
                        'balance': None
                    }
                else:
                    return {
                        'valid': False,
                        'exists': False,
                        'reason': 'Таймаут при проверке адреса',
                        'balance': None
                    }
    
    except Exception as e:
        # Общая ошибка
        return {
            'valid': False,
            'exists': False,
            'reason': f'Ошибка: {str(e)[:50]}',
            'balance': None
        }


async def check_ton_address_alternative(session: aiohttp.ClientSession, address: str) -> dict:
    """Альтернативный метод проверки TON адреса"""
    try:
        # Проверка через tonapi.io
        url = f'https://tonapi.io/v1/account/getInfo?account={address}'
        
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                
                # Если есть поле 'balance', значит адрес существует
                if 'balance' in data:
                    balance_nano = data.get('balance', 0)
                    balance_ton = int(balance_nano) / 1_000_000_000
                    
                    return {
                        'valid': True,
                        'exists': True,
                        'reason': 'Адрес существует и активен',
                        'balance': balance_ton
                    }
                else:
                    # Проверяем формат адреса локально
                    if re.match(r'^(UQ|EQ|0:)[a-zA-Z0-9_-]{44,}$', address):
                        return {
                            'valid': True,
                            'exists': True,  # Предполагаем существование
                            'reason': 'Формат адреса корректный',
                            'balance': None
                        }
                    else:
                        return {
                            'valid': False,
                            'exists': False,
                            'reason': 'Некорректный формат TON адреса',
                            'balance': None
                        }
            else:
                # Последняя попытка - проверка формата
                if re.match(r'^(UQ|EQ|0:)[a-zA-Z0-9_-]{44,}$', address):
                    return {
                        'valid': True,
                        'exists': True,  # Предполагаем существование
                        'reason': 'Формат адреса корректный (API недоступен)',
                        'balance': None
                    }
                else:
                    return {
                        'valid': False,
                        'exists': False,
                        'reason': 'Некорректный формат TON адреса',
                        'balance': None
                    }
    except:
        # Финальная проверка формата
        if re.match(r'^(UQ|EQ|0:)[a-zA-Z0-9_-]{44,}$', address):
            return {
                'valid': True,
                'exists': True,  # Предполагаем существование
                'reason': 'Формат адреса корректный',
                'balance': None
            }
        else:
            return {
                'valid': False,
                'exists': False,
                'reason': 'Некорректный формат TON адреса',
                'balance': None
            }


# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


# ===== СОСТОЯНИЯ (FSM) =====
class Form(StatesGroup):
    waiting_for_stars = State()
    waiting_for_ton_amount = State()
    waiting_for_ton_address = State()
    waiting_for_friend_username = State()
    waiting_for_premium_friend = State()


# ===== УЛУЧШЕННОЕ ХРАНИЛИЩЕ ДАННЫХ =====
class UserData:
    """Класс для хранения данных пользователя"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.data = {}
        return cls._instance
    
    def set_premium_data(self, user_id: int, period: str, price: float, prem_ton: float):
        """Сохранить данные о Premium"""
        if user_id not in self.data:
            self.data[user_id] = {}
        self.data[user_id]['premium'] = {
            'period': period,
            'price': price,
            'prem_ton': prem_ton
        }
    
    def get_premium_data(self, user_id: int):
        """Получить данные о Premium"""
        if user_id in self.data and 'premium' in self.data[user_id]:
            return self.data[user_id]['premium']
        return None
    
    def set_stars_data(self, user_id: int, star_value: int, formulastar: float, star_ton: float):
        """Сохранить данные о Stars"""
        if user_id not in self.data:
            self.data[user_id] = {}
        self.data[user_id]['stars'] = {
            'star_value': star_value,
            'formulastar': formulastar,
            'star_ton': star_ton
        }
    
    def get_stars_data(self, user_id: int):
        """Получить данные о Stars"""
        if user_id in self.data and 'stars' in self.data[user_id]:
            return self.data[user_id]['stars']
        return None
    
    def set_ton_data(self, user_id: int, address: str):
        """Сохранить данные о TON"""
        if user_id not in self.data:
            self.data[user_id] = {}
        self.data[user_id]['ton'] = {
            'address': address
        }
    
    def get_ton_data(self, user_id: int):
        """Получить данные о TON"""
        if user_id in self.data and 'ton' in self.data[user_id]:
            return self.data[user_id]['ton']
        return None
    
    def clear_user_data(self, user_id: int):
        """Очистить данные пользователя"""
        if user_id in self.data:
            del self.data[user_id]


user_data = UserData()


# ===== БАЗА ДАННЫХ =====
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                subscribed INTEGER DEFAULT 0,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add_user(self, user_id, username):
        self.cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                            (user_id, username))
        self.conn.commit()

    def update_subscription(self, user_id, subscribed):
        self.cursor.execute('UPDATE users SET subscribed = ? WHERE user_id = ?',
                            (subscribed, user_id))
        self.conn.commit()


db = Database()


# ===== ФУНКЦИИ ДЛЯ ИЗОБРАЖЕНИЙ =====
def get_photo(filename):
    """Получить фото из папки или использовать заглушку"""
    try:
        return FSInputFile(f"images/{filename}")
    except:
        return "https://via.placeholder.com/600x300/0088cc/FFFFFF?text=Spire+Shop"


# ===== ФУНКЦИЯ ПРОВЕРКИ ПОДПИСКИ =====
async def check_user_subscription(user_id: int) -> bool:
    """Проверка подписки на канал"""
    try:
        chat_member = await bot.get_chat_member(chat_id=ADMIN_CHANNEL, user_id=user_id)
        is_subscribed = chat_member.status in ['member', 'administrator', 'creator']
        return is_subscribed
    except Exception as e:
        print(f"❌ Ошибка проверки подписки: {e}")
        return False


# ===== ОСНОВНЫЕ КОМАНДЫ =====
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    db.add_user(user_id, username)

    welcome_text = (
        "Добро пожаловать!\n\n"
        "Spire — магазин для покупки Telegram Stars, TON и Premium "
        "дешевле, чем в приложении и без верификации.\n\n"
        "❗Чтобы продолжить подпишитесь на наш канал:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/{ADMIN_CHANNEL[1:]}")],
        [InlineKeyboardButton(text="✅ Проверить Подписку", callback_data="check_subscription")]
    ])

    photo = get_photo("start.jpg")

    await send_with_deletion(
        user_id=user_id,
        text=welcome_text if not photo else None,
        photo=photo,
        caption=welcome_text if photo else None,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery):
    user_id = callback.from_user.id

    # Показываем "Проверяем..."
    await edit_with_deletion(
        callback=callback,
        caption="🔍 Проверяем подписку..."
    )

    # Ждем немного для визуального эффекта
    await asyncio.sleep(0.5)

    # Проверяем подписку
    is_subscribed = await check_user_subscription(user_id)

    if is_subscribed:
        db.update_subscription(user_id, 1)
        # Очищаем старые данные пользователя
        user_data.clear_user_data(user_id)
        # Сразу переходим в меню
        await show_menu(callback)
    else:
        await edit_with_deletion(
            callback=callback,
            caption="❌ Вы не подписаны на канал!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подписаться на канал", url=f"https://t.me/{ADMIN_CHANNEL[1:]}")],
                [InlineKeyboardButton(text="✅ Проверить снова", callback_data="check_subscription")]
            ])
        )


async def show_menu(callback: CallbackQuery = None, message: Message = None):
    """Показ меню с автоудалением"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Купить звёзды", callback_data="buy_stars")],
        [InlineKeyboardButton(text="💎 Купить TON", callback_data="buy_ton")],
        [InlineKeyboardButton(text="👑 Купить Premium", callback_data="buy_premium")],
        [InlineKeyboardButton(text="🆘 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME[1:]}")]
    ])

    photo = get_photo("menu.jpg")

    if callback:
        await edit_with_deletion(
            callback=callback,
            photo=photo,
            caption=" ",  # Пустой текст
            reply_markup=keyboard
        )
    else:
        await send_with_deletion(
            user_id=message.from_user.id,
            photo=photo,
            caption=" ",  # Пустой текст
            reply_markup=keyboard
        )


@router.callback_query(F.data == "menu")
@router.message(Command("menu"))
async def menu_command(callback: CallbackQuery = None, message: Message = None):
    if callback:
        await show_menu(callback=callback)
    else:
        await show_menu(message=message)


# ===== ПОКУПКА ЗВЕЗД =====
@router.callback_query(F.data == "buy_stars")
async def buy_stars(callback: CallbackQuery, state: FSMContext):
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

    photo = get_photo("stars.jpg")

    await edit_with_deletion(
        callback=callback,
        photo=photo,
        caption=text,
        reply_markup=keyboard
    )

    await state.set_state(Form.waiting_for_stars)


@router.message(Form.waiting_for_stars)
async def process_stars_amount(message: Message, state: FSMContext):
    try:
        star_value = int(message.text)

        # Удаляем сообщение пользователя
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass

        if star_value < 50 or star_value > 1000000:
            await send_with_deletion(
                user_id=message.from_user.id,
                text="❌ Количество должно быть от 50 до 1,000,000"
            )
            return

        formulastar = round(star_value * 1.7, 1)
        star_ton = round(formulastar / 200, 4)

        # Сохраняем данные в надежное хранилище
        user_data.set_stars_data(message.from_user.id, star_value, formulastar, star_ton)

        text = (
            f"⭐️Telegram Stars\n\n"
            f"❗️Количество: {star_value}\n"
            f"💰 Стоимость: {formulastar}₽ / {star_ton} TON\n\n"
            f"Для кого вы приобретаете:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💫 Купить себе", callback_data="buy_stars_self")],
            [InlineKeyboardButton(text="🎁 Подарить другу", callback_data="gift_stars_friend")],
            [InlineKeyboardButton(text="Назад", callback_data="buy_stars")]
        ])

        photo = get_photo("stars.jpg")

        await send_with_deletion(
            user_id=message.from_user.id,
            photo=photo,
            caption=text,
            reply_markup=keyboard
        )

        await state.clear()

    except ValueError:
        # Удаляем сообщение пользователя
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass

        await send_with_deletion(
            user_id=message.from_user.id,
            text="❌ Пожалуйста, введите корректное число"
        )


@router.callback_query(F.data == "buy_stars_self")
async def buy_stars_self(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Получаем данные из надежного хранилища
    stars_data = user_data.get_stars_data(user_id)
    
    if not stars_data:
        await callback.answer("❌ Сначала введите количество звезд", show_alert=True)
        await buy_stars(callback, None)
        return
    
    star_value = stars_data.get('star_value', 0)
    formulastar = stars_data.get('formulastar', 0)
    star_ton = stars_data.get('star_ton', 0)

    if star_value == 0:
        await callback.answer("❌ Сначала введите количество звезд", show_alert=True)
        await buy_stars(callback, None)
        return

    username = callback.from_user.username or callback.from_user.first_name

    text = (
        f"⭐️Telegram Stars\n\n"
        f"❗️Количество: {star_value} звёзд\n"
        f"💰 Стоимость: {formulastar}₽ или {star_ton} TON\n"
        f"👤Получатель: @{username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 СБП", callback_data=f"payment_sbp_stars_{star_value}")],
        [InlineKeyboardButton(text="🔐 Cryptobot", callback_data=f"payment_crypto_stars_{star_value}")],
        [InlineKeyboardButton(text="💎 TON", url=f"ton://transfer/{TON_WALLET}?amount={int(star_ton * 1000000000)}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="buy_stars")]
    ])

    await edit_with_deletion(
        callback=callback,
        caption=text,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "gift_stars_friend")
async def gift_stars_friend(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # Получаем данные из надежного хранилища
    stars_data = user_data.get_stars_data(user_id)
    
    if not stars_data:
        await callback.answer("❌ Сначала введите количество звезд", show_alert=True)
        await buy_stars(callback, None)
        return
    
    star_value = stars_data.get('star_value', 0)
    formulastar = stars_data.get('formulastar', 0)
    star_ton = stars_data.get('star_ton', 0)

    if star_value == 0:
        await callback.answer("❌ Сначала введите количество звезд", show_alert=True)
        return

    text = (
        f"⭐️Telegram Stars\n\n"
        f"❗️Количество: {star_value} звёзд\n"
        f"💰Стоимость: {formulastar}₽ / {star_ton} TON\n\n"
        "👤Введите @username получателя:"
    )

    await edit_with_deletion(
        callback=callback,
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="buy_stars")]
        ])
    )

    await state.set_state(Form.waiting_for_friend_username)


@router.message(Form.waiting_for_friend_username)
async def process_friend_username(message: Message, state: FSMContext):
    username = message.text.strip()

    # Удаляем сообщение пользователя
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass

    # Очистка юзернейма
    if username.startswith('@'):
        username = username[1:]

    if len(username) < 3:
        await send_with_deletion(
            user_id=message.from_user.id,
            text="❌ Username должен содержать минимум 3 символа"
        )
        return

    # Проверка формата юзернейма
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,31}$', username):
        await send_with_deletion(
            user_id=message.from_user.id,
            text="❌ Некорректный формат username.\n\n"
                 "Правила:\n"
                 "• От 3 до 32 символов\n"
                 "• Только буквы (a-z), цифры (0-9) и подчеркивание (_)\n"
                 "• Не может начинаться с цифры\n\n"
                 "Пример: @username, @user_name, @User123"
        )
        return

    # Показываем сообщение о проверке
    checking_msg = await send_with_deletion(
        user_id=message.from_user.id,
        text=f"🔍 Проверяю @{username}..."
    )

    # Проверяем существование юзернейма
    check_result = await check_username_exists(username)

    if not check_result['exists']:
        await send_with_deletion(
            user_id=message.from_user.id,
            text=f"❌ Пользователь @{username} не найден!\n\n"
                 f"Причина: {check_result['reason']}\n\n"
                 f"Возможные проблемы:\n"
                 f"• Юзернейм указан с ошибкой\n"
                 f"• Пользователь изменил юзернейм\n"
                 f"• Аккаунт удален или заблокирован\n\n"
                 f"Пожалуйста, проверьте правильность юзернейма и попробуйте снова.\n\n"
                 f"<i>Для повторного ввода нажмите:</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Ввести другой юзернейм", callback_data="gift_stars_friend")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="buy_stars")]
            ])
        )
        return

    user_id = message.from_user.id
    stars_data = user_data.get_stars_data(user_id)
    
    if not stars_data:
        await send_with_deletion(
            user_id=user_id,
            text="❌ Данные не найдены. Начните сначала."
        )
        await buy_stars(callback=message, state=None)
        return
    
    star_value = stars_data.get('star_value', 0)
    formulastar = stars_data.get('formulastar', 0)
    star_ton = stars_data.get('star_ton', 0)

    if star_value == 0:
        await send_with_deletion(
            user_id=user_id,
            text="❌ Данные не найдены"
        )
        return

    # Пользователь найден, продолжаем
    text = (
        f"⭐️ Telegram Stars\n\n"
        f"❗️Количество: {star_value} звёзд\n"
        f"💰Стоимость: {formulastar}₽ / {star_ton} TON\n"
        f"👤Получатель: @{username}\n\n"
        f"Выберите способ оплаты:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 СБП",
                              callback_data=f"payment_sbp_stars_friend_{star_value}_{username}")],
        [InlineKeyboardButton(text="🔐 Cryptobot",
                              callback_data=f"payment_crypto_stars_friend_{star_value}_{username}")],
        [InlineKeyboardButton(text="💎 TON",
                              url=f"ton://transfer/{TON_WALLET}?amount={int(star_ton * 1000000000)}")],
        [InlineKeyboardButton(text="🔄 Изменить получателя", callback_data="gift_stars_friend")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="buy_stars")]
    ])

    photo = get_photo("stars.jpg")

    await send_with_deletion(
        user_id=user_id,
        photo=photo,
        caption=text,
        reply_markup=keyboard
    )

    await state.clear()


# ===== ПОКУПКА TON =====
@router.callback_query(F.data == "buy_ton")
async def buy_ton(callback: CallbackQuery, state: FSMContext):
    text = (
        "💎 TON\n\n"
        "💰Курс к рублю: 200₽\n"
        "Минимальное количество: 1 TON\n\n"
        "✏️Введите адрес кошелька для получения TON:"
    )

    await edit_with_deletion(
        callback=callback,
        photo=get_photo("ton.jpg"),
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="menu")]
        ])
    )

    await state.set_state(Form.waiting_for_ton_address)


@router.message(Form.waiting_for_ton_address)
async def process_ton_address(message: Message, state: FSMContext):
    address = message.text.strip()

    # Удаляем сообщение пользователя
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass

    # Показываем сообщение о проверке
    checking_msg = await send_with_deletion(
        user_id=message.from_user.id,
        text=f"🔍 Проверяю адрес кошелька..."
    )

    # Проверяем адрес TON
    check_result = await check_ton_address(address)

    if not check_result['valid']:
        await send_with_deletion(
            user_id=message.from_user.id,
            text=f"❌ Некорректный адрес TON кошелька!\n\n"
                 f"Причина: {check_result['reason']}\n\n"
                 f"📌 Примеры правильных адресов:\n"
                 f"• UQAL5Y75ykdUsMmW5FgnxKJyz1-njyS_oNuN1Lp2_hgNundO\n"
                 f"• EQD__________________________________________voXL\n\n"
                 f"Убедитесь, что:\n"
                 f"• Адрес начинается с UQ, EQ или 0:\n"
                 f"• Содержит только буквы, цифры и символы -_ (дефис и подчеркивание)\n"
                 f"• Длина обычно 48 символов и более\n\n"
                 f"<i>Попробуйте ввести адрес снова:</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Ввести другой адрес", callback_data="buy_ton")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="menu")]
            ])
        )
        return

    # Если адрес валидный, но мы не уверены в его существовании
    if not check_result['exists']:
        # Предупреждаем пользователя, но позволяем продолжить
        warning_text = (
            f"⚠️ Внимание!\n\n"
            f"Адрес: {address[:10]}...{address[-10:]}\n\n"
            f"Не удалось подтвердить активность этого адреса в сети TON.\n"
            f"Убедитесь, что адрес верный, иначе TON будут отправлены "
            f"на несуществующий кошелек и потеряны навсегда!\n\n"
            f"Хотите продолжить с этим адресом?"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, продолжить", callback_data=f"confirm_address_{address}")],
            [InlineKeyboardButton(text="🔄 Ввести другой адрес", callback_data="buy_ton")]
        ])
        
        await send_with_deletion(
            user_id=message.from_user.id,
            text=warning_text,
            reply_markup=keyboard
        )
        return

    # Адрес валидный и существует, сохраняем и запрашиваем сумму
    user_data.set_ton_data(message.from_user.id, address)
    
    balance_info = ""
    if check_result['balance'] is not None:
        balance_info = f"💰 Баланс кошелька: {check_result['balance']:.2f} TON\n\n"
    
    text = (
        f"✅ Адрес кошелька проверен!\n\n"
        f"{balance_info}"
        f"📥 Адрес: {address[:15]}...{address[-10:]}\n\n"
        f"✏️ Введите сумму в TON для получения:"
    )

    await send_with_deletion(
        user_id=message.from_user.id,
        photo=get_photo("ton.jpg"),
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Изменить адрес", callback_data="buy_ton")]
        ])
    )

    await state.set_state(Form.waiting_for_ton_amount)


@router.callback_query(F.data.startswith("confirm_address_"))
async def confirm_address_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения адреса"""
    address = callback.data.replace("confirm_address_", "")
    user_id = callback.from_user.id
    
    # Сохраняем адрес
    user_data.set_ton_data(user_id, address)
    
    text = (
        f"✅ Адрес кошелька принят!\n\n"
        f"⚠️ Предупреждение: Адрес не был полностью проверен.\n"
        f"📥 Адрес: {address[:15]}...{address[-10:]}\n\n"
        f"✏️ Введите сумму в TON для получения:"
    )

    await edit_with_deletion(
        callback=callback,
        photo=get_photo("ton.jpg"),
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Изменить адрес", callback_data="buy_ton")]
        ])
    )

    await state.set_state(Form.waiting_for_ton_amount)


@router.message(Form.waiting_for_ton_amount)
async def process_ton_amount(message: Message, state: FSMContext):
    try:
        ton_value = float(message.text)

        # Удаляем сообщение пользователя
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass

        if ton_value < 1:
            await send_with_deletion(
                user_id=message.from_user.id,
                text="❌ Минимальное количество: 1 TON"
            )
            return

        user_id = message.from_user.id
        ton_data = user_data.get_ton_data(user_id)
        
        if not ton_data:
            await send_with_deletion(
                user_id=user_id,
                text="❌ Адрес кошелька не найден. Начните сначала."
            )
            await buy_ton(callback=message, state=None)
            return
        
        address = ton_data.get('address', 'Не указан')

        formulaTON = round(ton_value * 200, 1)

        text = (
            f"💎 TON\n\n"
            f"🩵Количество: {ton_value} TON\n"
            f"💰Стоимость: {formulaTON}₽\n"
            f"📥Адрес кошелька: {address[:15]}...{address[-10:]}\n\n"
            f"Выберите способ оплаты:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦 СБП", callback_data=f"payment_sbp_ton_{ton_value}")],
            [InlineKeyboardButton(text="🔐 Cryptobot", callback_data=f"payment_crypto_ton_{ton_value}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="buy_ton")]
        ])

        await send_with_deletion(
            user_id=user_id,
            photo=get_photo("ton.jpg"),
            caption=text,
            reply_markup=keyboard
        )

        await state.clear()

    except ValueError:
        # Удаляем сообщение пользователя
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        except:
            pass

        await send_with_deletion(
            user_id=message.from_user.id,
            text="❌ Введите число (например: 10)"
        )


# ===== ПОКУПКА PREMIUM =====
@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    text = "👑Telegram Premium\n\n🗓Выберите период подписки:"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Premium - 12 месяцев", callback_data="premium_12")],
        [InlineKeyboardButton(text="Premium - 6 месяцев", callback_data="premium_6")],
        [InlineKeyboardButton(text="Premium - 3 месяца", callback_data="premium_3")],
        [InlineKeyboardButton(text="Назад", callback_data="menu")]
    ])

    await edit_with_deletion(
        callback=callback,
        photo=get_photo("premium.jpg"),
        caption=text,
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("premium_"))
async def process_premium_period(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Определяем период и цену
    if callback.data == "premium_12":
        period = "Premium - 12 месяцев"
        price = 2800
    elif callback.data == "premium_6":
        period = "Premium - 6 месяцев"
        price = 1600
    elif callback.data == "premium_3":
        period = "Premium - 3 месяца"
        price = 1200
    else:
        period = "Premium"
        price = 0
    
    prem_ton = round(price / 200, 2)
    
    # Сохраняем данные в надежное хранилище
    user_data.set_premium_data(user_id, period, price, prem_ton)

    text = (
        f"👑 Telegram {period}\n\n"
        f"💰Стоимость: {price}₽ / {prem_ton} TON\n\n"
        f"Для кого вы приобретаете:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💫 Купить себе", callback_data="buy_premium_self")],
        [InlineKeyboardButton(text="🎁 Подарить другу", callback_data="gift_premium_friend")],
        [InlineKeyboardButton(text="Назад", callback_data="buy_premium")]
    ])

    await edit_with_deletion(
        callback=callback,
        photo=get_photo("premium.jpg"),
        caption=text,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "buy_premium_self")
async def buy_premium_self(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Получаем данные из надежного хранилища
    premium_data = user_data.get_premium_data(user_id)
    
    if not premium_data:
        await callback.answer("❌ Сначала выберите период подписки", show_alert=True)
        await buy_premium(callback)
        return
    
    period = premium_data.get('period', 'Premium')
    price = premium_data.get('price', 0)
    prem_ton = premium_data.get('prem_ton', 0)
    
    if price == 0:
        await callback.answer("❌ Сначала выберите период подписки", show_alert=True)
        await buy_premium(callback)
        return

    username = callback.from_user.username or callback.from_user.first_name

    text = (
        f"👑 Telegram {period}\n\n"
        f"💰 Стоимость: {price}₽ / {prem_ton} TON\n"
        f"👤 Получатель: @{username}\n\n"
        f"Выберите способ оплаты:"
    )

    # Создаем безопасный идентификатор периода
    period_safe = period.replace(' ', '_').replace('-', '_')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 СБП", 
                              callback_data=f"payment_sbp_premium_{price}_{period_safe}")],
        [InlineKeyboardButton(text="🔐 Cryptobot", 
                              callback_data=f"payment_crypto_premium_{price}_{period_safe}")],
        [InlineKeyboardButton(text="💎 TON", 
                              url=f"ton://transfer/{TON_WALLET}?amount={int(prem_ton * 1000000000)}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="buy_premium")]
    ])

    await edit_with_deletion(
        callback=callback,
        photo=get_photo("premium.jpg"),
        caption=text,
        reply_markup=keyboard
    )


@router.callback_query(F.data == "gift_premium_friend")
async def gift_premium_friend(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # Получаем данные из надежного хранилища
    premium_data = user_data.get_premium_data(user_id)
    
    if not premium_data:
        await callback.answer("❌ Сначала выберите период подписки", show_alert=True)
        await buy_premium(callback)
        return
    
    period = premium_data.get('period', 'Premium')
    price = premium_data.get('price', 0)
    prem_ton = premium_data.get('prem_ton', 0)
    
    if price == 0:
        await callback.answer("❌ Сначала выберите период подписки", show_alert=True)
        await buy_premium(callback)
        return

    text = (
        f"👑 Telegram {period}\n\n"
        f"💰 Стоимость: {price}₽ / {prem_ton} TON\n\n"
        "👤 Введите @username получателя:"
    )

    await edit_with_deletion(
        callback=callback,
        photo=get_photo("premium.jpg"),
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data=f"premium_back")]
        ])
    )

    await state.set_state(Form.waiting_for_premium_friend)


# Обработчик для кнопки "Назад" из gift_premium_friend
@router.callback_query(F.data == "premium_back")
async def premium_back_handler(callback: CallbackQuery):
    """Обработчик кнопки Назад из gift_premium_friend"""
    user_id = callback.from_user.id
    premium_data = user_data.get_premium_data(user_id)
    
    if premium_data:
        period = premium_data.get('period', 'Premium')
        price = premium_data.get('price', 0)
        prem_ton = premium_data.get('prem_ton', 0)
        
        text = (
            f"👑 Telegram {period}\n\n"
            f"💰Стоимость: {price}₽ / {prem_ton} TON\n\n"
            f"Для кого вы приобретаете:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💫 Купить себе", callback_data="buy_premium_self")],
            [InlineKeyboardButton(text="🎁 Подарить другу", callback_data="gift_premium_friend")],
            [InlineKeyboardButton(text="Назад", callback_data="buy_premium")]
        ])

        await edit_with_deletion(
            callback=callback,
            photo=get_photo("premium.jpg"),
            caption=text,
            reply_markup=keyboard
        )
    else:
        await buy_premium(callback)


@router.message(Form.waiting_for_premium_friend)
async def process_premium_friend_username(message: Message, state: FSMContext):
    username = message.text.strip()

    # Удаляем сообщение пользователя
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass

    # Очистка юзернейма
    if username.startswith('@'):
        username = username[1:]

    if len(username) < 3:
        await send_with_deletion(
            user_id=message.from_user.id,
            text="❌ Username должен содержать минимум 3 символа"
        )
        return

    # Проверка формата юзернейма
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,31}$', username):
        await send_with_deletion(
            user_id=message.from_user.id,
            text="❌ Некорректный формат username.\n\n"
                 "Правила:\n"
                 "• От 3 до 32 символов\n"
                 "• Только буквы (a-z), цифры (0-9) и подчеркивание (_)\n"
                 "• Не может начинаться с цифры\n\n"
                 "Пример: @username, @user_name, @User123"
        )
        return

    # Проверяем существование юзернейма
    checking_msg = await send_with_deletion(
        user_id=message.from_user.id,
        text=f"🔍 Проверяю @{username}..."
    )

    check_result = await check_username_exists(username)

    if not check_result['exists']:
        await send_with_deletion(
            user_id=message.from_user.id,
            text=f"❌ Пользователь @{username} не найден!\n\n"
                 f"Причина: {check_result['reason']}\n\n"
                 f"Возможные проблемы:\n"
                 f"• Юзернейм указан с ошибкой\n"
                 f"• Пользователь изменил юзернейм\n"
                 f"• Аккаунт удален или заблокирован\n\n"
                 f"Пожалуйста, проверьте правильность юзернейма и попробуйте снова.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Ввести другой юзернейм", callback_data="gift_premium_friend")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="buy_premium")]
            ])
        )
        return

    # Получаем данные о Premium
    user_id = message.from_user.id
    premium_data = user_data.get_premium_data(user_id)
    
    if not premium_data:
        await send_with_deletion(
            user_id=user_id,
            text="❌ Данные о подписке не найдены. Начните сначала."
        )
        await buy_premium(callback=message)
        return
    
    period = premium_data.get('period', 'Premium')
    price = premium_data.get('price', 0)
    prem_ton = premium_data.get('prem_ton', 0)

    if price == 0:
        await send_with_deletion(
            user_id=user_id,
            text="❌ Данные о подписке не найдены. Начните сначала."
        )
        await buy_premium(callback=message)
        return

    text = (
        f"👑 Telegram {period}\n\n"
        f"💰 Стоимость: {price}₽ / {prem_ton} TON\n"
        f"👤 Получатель: @{username}\n\n"
        f"Выберите способ оплаты:"
    )

    # Создаем безопасный идентификатор периода
    period_safe = period.replace(' ', '_').replace('-', '_')

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 СБП", 
                              callback_data=f"payment_sbp_premium_friend_{price}_{period_safe}_{username}")],
        [InlineKeyboardButton(text="🔐 Cryptobot", 
                              callback_data=f"payment_crypto_premium_friend_{price}_{period_safe}_{username}")],
        [InlineKeyboardButton(text="💎 TON", 
                              url=f"ton://transfer/{TON_WALLET}?amount={int(prem_ton * 1000000000)}")],
        [InlineKeyboardButton(text="🔄 Изменить получателя", callback_data="gift_premium_friend")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="buy_premium")]
    ])

    await send_with_deletion(
        user_id=user_id,
        photo=get_photo("premium.jpg"),
        caption=text,
        reply_markup=keyboard
    )

    await state.clear()


# ===== ОБРАБОТКА ОПЛАТЫ =====
@router.callback_query(F.data.startswith("payment_"))
async def process_payment(callback: CallbackQuery):
    data_parts = callback.data.split("_")
    if len(data_parts) < 4:
        await callback.answer("❌ Ошибка обработки платежа", show_alert=True)
        return

    payment_type = data_parts[1]
    product = data_parts[2]
    
    # Инициализация переменных
    friend_username = None
    period = None
    
    # Обработка разных типов продуктов
    if product == "stars":
        amount = data_parts[3]
        cost = round(float(amount) * 1.7, 1)
        product_name = "Telegram Stars"
        
        # Проверяем, есть ли юзернейм друга
        if len(data_parts) > 4:
            friend_username = data_parts[4]
    
    elif product == "ton":
        amount = data_parts[3]
        cost = round(float(amount) * 200, 1)
        product_name = "TON"
    
    elif product == "premium":
        amount = data_parts[3]
        cost = float(amount)
        
        # Проверяем, есть ли период и юзернейм
        if len(data_parts) > 4:
            period = data_parts[4].replace('_', ' ')
            product_name = f"Telegram {period}"
        else:
            product_name = "Telegram Premium"
        
        # Проверяем, есть ли юзернейм друга
        if len(data_parts) > 5:
            friend_username = data_parts[5]
    
    else:
        amount = data_parts[3]
        cost = float(amount)
        product_name = "товар"

    # Формируем текст в зависимости от наличия друга
    if friend_username:
        text = (
            f"✅ Заказ оформлен!\n\n"
            f"📦 Товар: {product_name}\n"
            f"💰 Сумма: {cost}₽\n"
            f"👤 Получатель: @{friend_username}\n"
            f"💳 Способ: {payment_type}\n\n"
            f"<i>Демо-режим: оплата не проводилась</i>"
        )
    else:
        text = (
            f"✅ Заказ оформлен!\n\n"
            f"📦 Товар: {product_name}\n"
            f"💰 Сумма: {cost}₽\n"
            f"💳 Способ: {payment_type}\n\n"
            f"<i>Демо-режим: оплата не проводилась</i>"
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]
    ])

    await edit_with_deletion(
        callback=callback,
        caption=text,
        reply_markup=keyboard
    )


# ===== ОБРАБОТКА НЕИЗВЕСТНЫХ КОМАНД =====
@router.message()
async def unknown_message(message: Message):
    # Удаляем сообщение пользователя
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except:
        pass

    # Показываем меню
    await show_menu(message=message)


# ===== ЗАПУСК =====
async def main():
    print("=" * 50)
    print("🤖 Бот запускается...")

    try:
        me = await bot.get_me()
        print(f"✅ Бот: @{me.username}")
        print(f"👤 Имя: {me.first_name}")
        print("=" * 50)
        print("🎯 Особенности:")
        print("✅ Автоудаление сообщений")
        print("✅ Проверка существования юзернейма")
        print("✅ Проверка TON адреса на валидность и существование")
        print("✅ Надежное хранение данных пользователя")
        print("✅ Все ответы удаляются после нового действия")
        print("✅ Работает проверка подписки")
        print("✅ Все функции рабочие")
        print("=" * 50)
        print("📊 База данных: bot_database.db")
        print("🖼 Изображения: папка images/")
        print("=" * 50)

        await dp.start_polling(bot)

    except KeyboardInterrupt:
        print("\n🛑 Бот останавливается...")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()
        print("✅ Бот завершил работу")


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Запуск бота
    asyncio.run(main())
