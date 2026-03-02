# username_checker.py
from telethon import TelegramClient
import os
from dotenv import load_dotenv
load_dotenv()

STRING_SESSION = os.getenv("STRING_SESSION")
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
PASSWORD = "Serzh011" # 🔥 ПАРОЛЬ 2FA (если есть)

# ===== CRYPTOBOT НАСТРОЙКИ =====
CRYPTO_TOKEN = "513952:AA8SvhV7y2TSGXIsQ1Sjmu1jc6CZPxDAgJZ"
BOT_USERNAME = "spireshoptgbot"

# ===== КЭШ ДЛЯ USERNAME =====
username_cache = {}
CACHE_TIME = 300  # 5 минут

# ===== TELETHON КЛИЕНТ =====
# Создаем клиента один раз и используем его постоянно
client = TelegramClient('telegram_session', API_ID, API_HASH)
client_ready = False


async def ensure_client():
    """
    Подключает клиента Telethon если ещё не подключен.
    Вызывается перед каждым использованием Telethon.
    """
    global client_ready
    if not client_ready:
        try:
            print("🔄 Подключение к Telethon...")
            await client.connect()

            if not await client.is_user_authorized():
                # Если нет сессии - запрашиваем код
                await client.send_code_request(PHONE)
                print(f"📱 Код отправлен на {PHONE}")

                # ВНИМАНИЕ: здесь нужно ввести код в консоли!
                # Это произойдет только при первом запуске
                code = input("🔐 Введи код из Telegram: ").strip()

                try:
                    await client.sign_in(phone=PHONE, code=code)
                except SessionPasswordNeededError:
                    # Если включена двухфакторка
                    pwd = input("🔑 Введи облачный пароль: ").strip()
                    await client.sign_in(password=pwd)

            me = await client.get_me()
            print(f"✅ Telethon готов! Аккаунт: @{me.username}")
            client_ready = True

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
