# username_checker.py
from telethon import TelegramClient
from telethon.errors import UsernameInvalidError, FloodWaitError
import asyncio
import aiohttp
import time
import json

# ===== ТВОИ ДАННЫЕ =====
API_ID = 31990778  # 🔥 ЗАМЕНИ
API_HASH = '6d72f5bffdabc0a648943c49c4d95fd3'  # 🔥 ЗАМЕНИ
PHONE = '+79094717005'  # 🔥 ЗАМЕНИ
PASSWORD = 'Serzh011'  # 🔥 ЗАМЕНИ

# ===== CRYPTOBOT НАСТРОЙКИ =====
CRYPTO_TOKEN = "513952:AA8SvhV7y2TSGXIsQ1Sjmu1jc6CZPxDAgJZ"  # 🔥 ТВОЙ ТОКЕН
BOT_USERNAME = "spireshoptgbot"  # 🔥 ТВОЙ БОТ

# ===== НАСТРОЙКИ КЭША =====
username_cache = {}
CACHE_TIME = 300  # 5 минут

# СОЗДАЕМ КЛИЕНТА 1 РАЗ
client = TelegramClient('telegram_session', API_ID, API_HASH)
client_ready = False


async def ensure_client():
    """Подключает клиент один раз и держит открытым"""
    global client_ready
    if not client_ready:
        print("🔄 Подключение к Telethon...")
        await client.start(phone=PHONE, password=PASSWORD)
        client_ready = True
        me = await client.get_me()
        print(f"✅ Telethon подключен как @{me.username}")


async def _real_check_username(username: str):
    """Реальная проверка через Telethon"""
    try:
        # Очищаем username
        username = username.strip().replace('@', '')
        if not username:
            return {'exists': False, 'error': '❌ Пустой username'}

        # Убеждаемся что клиент подключен
        await ensure_client()

        # Получаем информацию (быстро, т.к. клиент уже подключен)
        user = await client.get_entity(username)

        # Проверяем Premium
        is_premium = False
        if hasattr(user, 'premium'):
            is_premium = user.premium

        return {
            'exists': True,
            'user_id': user.id,
            'username': user.username,
            'premium': is_premium
        }

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


async def check_username(username: str):
    """Проверка с кэшированием"""
    # Очищаем username
    clean_username = username.strip().replace('@', '')

    # Проверяем кэш
    if clean_username in username_cache:
        data, timestamp = username_cache[clean_username]
        if time.time() - timestamp < CACHE_TIME:
            print(f"📦 Кэш: @{clean_username}")
            return data

    # Если нет в кэше - проверяем
    print(f"🔍 Проверка: @{clean_username}")
    result = await _real_check_username(clean_username)

    # Сохраняем в кэш (только если нашли)
    if result['exists']:
        username_cache[clean_username] = (result, time.time())
        # Ограничиваем размер кэша
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


# ===== CRYPTOBOT ФУНКЦИИ =====
async def create_crypto_invoice(amount_rub: float, description: str = "", payload: str = ""):
    """Создает счет в CryptoBot"""
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
        "expires_in": 3600
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
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
                return {"success": False, "error": f"HTTP {response.status}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def check_invoice_status(invoice_id: str):
    """Проверяет статус счета"""
    url = "https://pay.crypt.bot/api/getInvoices"

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_TOKEN
    }

    params = {
        "invoice_ids": invoice_id
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok") and data.get("result", {}).get("items"):
                        invoice = data["result"]["items"][0]
                        return {"success": True, "status": invoice["status"]}
                return {"success": False, "status": "unknown"}
    except Exception as e:
        return {"success": False, "status": "error"}


async def close_client():
    """Закрывает клиент (при выключении бота)"""
    global client_ready
    if client_ready:
        await client.disconnect()
        client_ready = False
        print("👋 Telethon отключен")
