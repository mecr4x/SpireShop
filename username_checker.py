# username_checker.py
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import UsernameInvalidError, FloodWaitError, SessionPasswordNeededError
import aiohttp
import asyncio
import time
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (если есть)
load_dotenv()

# ===== ТВОИ ДАННЫЕ (ЗАПОЛНИ ОБЯЗАТЕЛЬНО) =====
# Можно указать прямо здесь или в .env файле
API_ID = 31990778  # 🔥 ТВОЙ API ID (число)
API_HASH = "6d72f5bffdabc0a648943c49c4d95fd3"  # 🔥 ТВОЙ API HASH
PHONE = "+79094717005"  # 🔥 ТВОЙ НОМЕР ТЕЛЕФОНА
PASSWORD = "Serzh011"  # 🔥 ПАРОЛЬ 2FA (если есть)

# ===== СТРОКА СЕССИИ (полученная из генератора) =====
STRING_SESSION = "1ApWapzMBu2nJAkIdDGcUQi2N7ToNOaX_q735Lew6U_WxU5FmlD-flNGsAl29jOK81AnawXdC4mEBlSJFEloW0SHGVb5X6oX19iupFfSjE5Ih5Z_hiniiTXQJNXs1cNpjoUvNw5K2XqoiOHPVjZappyJT3HbQ_MveWzd0llJ_v2Uyj_7OGMMpMdgCJASSQRLuwMm7SmoYS42L61-F8g0jB4UCIo_6MW9P_meZXx5_XARRRRFW-gblOQ0k6YFG96eK_WAsVZwjYuDnNm3sA-qwuXuI2gTX4T2UcFWVDiBp25E0Q-DRZETO_GadWafaLVOMtIvt5mn18G0UyqOf7Zwo_MZY5aLGyC8="

# ===== CRYPTOBOT НАСТРОЙКИ =====
CRYPTO_TOKEN = "513952:AA8SvhV7y2TSGXIsQ1Sjmu1jc6CZPxDAgJZ"
BOT_USERNAME = "spireshoptgbot"

# ===== КЭШ ДЛЯ USERNAME =====
username_cache = {}
CACHE_TIME = 300  # 5 минут

# ===== TELETHON КЛИЕНТ С STRING SESSION =====
# Используем строковую сессию вместо файла
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
client_ready = True  # Уже готов, так как используем сессию

async def ensure_client():
    """
    Проверяет что клиент подключен.
    """
    global client_ready
    if not client_ready:
        try:
            print("🔄 Подключение к Telethon...")
            await client.connect()
            client_ready = True
            me = await client.get_me()
            print(f"✅ Telethon готов! Аккаунт: @{me.username}")
        except Exception as e:
            print(f"❌ Ошибка подключения Telethon: {e}")
            client_ready = False
    return client_ready

async def check_username(username: str) -> dict:
    """
    Проверяет существование username в Telegram.
    Возвращает словарь с информацией о пользователе.
    """
    # Очищаем username от @ и пробелов
    clean_username = username.strip().replace('@', '')

    if not clean_username:
        return {'exists': False, 'error': '❌ Пустой username'}

    # Проверяем кэш
    if clean_username in username_cache:
        data, timestamp = username_cache[clean_username]
        if time.time() - timestamp < CACHE_TIME:
            print(f"📦 Кэш: @{clean_username}")
            return data

    # Если нет в кэше - проверяем через Telethon
    print(f"🔍 Проверка: @{clean_username}")

    try:
        # Убеждаемся что клиент подключен
        await ensure_client()

        # Получаем информацию о пользователе
        user = await client.get_entity(clean_username)

        # Проверяем Premium статус
        is_premium = False
        if hasattr(user, 'premium'):
            is_premium = user.premium

        result = {
            'exists': True,
            'user_id': user.id,
            'username': user.username,
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', ''),
            'premium': is_premium,
            'premium_status': '✅ Есть Premium' if is_premium else '❌ Нет Premium',
            'bot': user.bot if hasattr(user, 'bot') else False,
            'verified': getattr(user, 'verified', False)
        }

        # Сохраняем в кэш
        username_cache[clean_username] = (result, time.time())

        # Ограничиваем размер кэша (оставляем последние 100)
        if len(username_cache) > 100:
            # Удаляем старые записи
            now = time.time()
            to_delete = []
            for name, (_, ts) in username_cache.items():
                if now - ts > CACHE_TIME:
                    to_delete.append(name)
            for name in to_delete:
                del username_cache[name]

        return result

    except UsernameInvalidError:
        return {'exists': False, 'error': '❌ Пользователь не найден'}
    except FloodWaitError as e:
        return {'exists': False, 'error': f'❌ Слишком много запросов, подождите {e.seconds}с'}
    except ValueError as e:
        if 'Cannot find any entity' in str(e):
            return {'exists': False, 'error': '❌ Пользователь не найден'}
        return {'exists': False, 'error': f'❌ Ошибка: {str(e)}'}
    except Exception as e:
        return {'exists': False, 'error': '❌ Пользователь не найден'}

# ===== CRYPTOBOT ФУНКЦИИ =====
async def create_crypto_invoice(amount_rub: float, description: str = "", payload: str = ""):
    """
    Создает счет в CryptoBot на сумму в рублях.
    Возвращает ссылку для оплаты.
    """
    url = "https://pay.crypt.bot/api/createInvoice"

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_TOKEN,
        "Content-Type": "application/json"
    }

    data = {
        "asset": "TON",
        "amount": str(amount_rub),
        "currency_type": "fiat",
        "fiat": "RUB",
        "description": description[:64],
        "payload": payload or f"pay_{int(time.time())}",
        "expires_in": 3600,
        "paid_btn_name": "openBot",
        "paid_btn_url": f"https://t.me/{BOT_USERNAME}",
        "allow_comments": False,
        "allow_anonymous": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers, timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        invoice = result["result"]
                        return {
                            "success": True,
                            "invoice_id": invoice["invoice_id"],
                            "pay_url": invoice.get("bot_invoice_url"),
                            "amount_rub": amount_rub
                        }
                    else:
                        error_msg = result.get('error', {}).get('message', 'Неизвестная ошибка')
                        return {"success": False, "error": error_msg}
                else:
                    return {"success": False, "error": f"HTTP {response.status}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def check_invoice_status(invoice_id: str):
    """
    Проверяет статус счета в CryptoBot.
    Возвращает статус: active, paid, expired
    """
    url = "https://pay.crypt.bot/api/getInvoices"

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_TOKEN
    }

    params = {
        "invoice_ids": invoice_id
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok") and data.get("result", {}).get("items"):
                        invoice = data["result"]["items"][0]
                        return {"success": True, "status": invoice["status"]}
                return {"success": False, "status": "unknown"}
    except Exception as e:
        return {"success": False, "status": "error"}

# ===== ФУНКЦИЯ ДЛЯ ЗАКРЫТИЯ КЛИЕНТА =====
async def close_client():
    """Закрывает клиент Telethon (вызывать при остановке бота)"""
    global client_ready
    if client_ready:
        await client.disconnect()
        client_ready = False
        print("👋 Telethon отключен")

# ===== ТЕСТОВЫЙ ЗАПУСК =====
if __name__ == "__main__":
    async def test():
        print("🔍 Тест Telethon и CryptoBot...")

        # Тест проверки username
        result = await check_username('durov')
        print(f"Результат проверки: {result}")

        # Тест CryptoBot
        print("\n🔍 Тест CryptoBot...")
        invoice = await create_crypto_invoice(100, "Тестовый платеж")
        print(f"Результат: {invoice}")

        await close_client()

    asyncio.run(test())
