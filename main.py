import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

BOT_TOKEN = "8236812443:AAGsoEmE7u9q5eBpKTQ3vlbp4IregP9-oHY"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Заглушка для Render
async def dummy_server():
    app = web.Application()
    async def handle(request):
        return web.Response(text="Bot is running")
    app.router.add_get('/', handle)
    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Заглушка на порту {port}")

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("✅ Бот работает!")

async def main():
    # Запускаем заглушку
    asyncio.create_task(dummy_server())
    
    print("🚀 Запуск тестового бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
