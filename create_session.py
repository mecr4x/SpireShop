from telethon import TelegramClient

API_ID = 31990778  # твой
API_HASH = '6d72f5bffdabc0a648943c49c4d95fd3'
PHONE = '+79001234567'

client = TelegramClient('telegram_session', API_ID, API_HASH)

async def main():
    await client.start(phone=PHONE)
    print("✅ Сессия создана!")
    await client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
