# config.py - рабочий вариант
import os

# ==== НАСТРОЙТЕ ЭТИ ЗНАЧЕНИЯ ====
BOT_TOKEN = "8236812443:AAGsoEmE7u9q5eBpKTQ3vlbp4IregP9-oHY"  # <-- ВАЖНО: замените на реальный токен!
CRYPTOBOT_TOKEN = "AA8SvhV7y2TSGXIsQ1Sjmu1jc6CZPxDAgJZ"  # Пока можно оставить пустым
FRAGMENT_API_KEY = "2f0d324620350722fabd87d464f3fb359193ef4850f2d7bbe0cf60005805c433"
TON_PRICE= 140
API_FRAGMENT_URL= "https://fragment-api.net/#/"


# =================================

# Остальные настройки
ADMIN_CHANNEL = '@spireshop01'
SUPPORT_USERNAME = '@adamyan_ss'
TON_WALLET = 'UQAL5Y75ykdUsMmW5FgnxKJyz1-njyS_oNuN1Lp2_hgNundO'
STAR_PRICE = 1.7
TON_MARKUP = 11
CRYPTOBOT_API = 'https://pay.crypt.bot/api'
TON_API = 'https://tonapi.io/v2'

# Проверка токена
if not BOT_TOKEN or "ВСТАВЬТЕ_ВАШ_ТОКЕН" in BOT_TOKEN:
    print("\n" + "="*60)
    print("❌ ВНИМАНИЕ: Токен бота не указан!")
    print("="*60)
    print("Чтобы получить токен:")
    print("1. Откройте Telegram")
    print("2. Найдите @BotFather")
    print("3. Отправьте /newbot")
    print("4. Создайте бота и скопируйте токен")
    print("5. Токен выглядит как: 1234567890:AABbCcDdEeFf...")
    print("="*60)
    exit(1)
