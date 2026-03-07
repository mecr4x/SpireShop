## webhook_server.py
from aiohttp import web
import json
import asyncio
from aiogram import Bot

BOT_TOKEN = "8236812443:AAGsoEmE7u9q5eBpKTQ3vlbp4IregP9-oHY"
ADMIN_CHANNEL = '@spireshop01'
bot = Bot(token=BOT_TOKEN)

processed_transactions = set()

async def platega_webhook(request):
    try:
        data = await request.json()
        print(f"📩 Platega webhook: {json.dumps(data, indent=2)}")
        
        transaction_id = data.get('transactionId')
        status = data.get('status')
        payload = data.get('payload', '')
        
        if transaction_id in processed_transactions:
            return web.Response(text="OK", status=200)
        processed_transactions.add(transaction_id)
        
        if status == 'SUCCESS' and payload:
            parts = payload.split('_')
            if len(parts) >= 2:
                user_id = int(parts[1])
                ptype = parts[0]
                amount = data.get('paymentDetails', {}).get('amount', 0)
                
                username = "неизвестно"
                try:
                    user = await bot.get_chat(user_id)
                    username = user.username or f"id{user_id}"
                except:
                    username = f"id{user_id}"
                
                await bot.send_message(
                    user_id,
                    f"✅ <b>Оплата подтверждена!</b>\n\n"
                    f"Спасибо за покупку!\n"
                    f"Товар: {ptype.upper()}\n"
                    f"Сумма: {amount}₽\n\n"
                    f"/menu — вернуться в меню"
                )
                
                admin_text = (
                    f"💰 <b>Новый платёж!</b>\n\n"
                    f"👤 <b>Пользователь:</b> @{username}\n"
                    f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                    f"📦 <b>Товар:</b> {ptype.upper()}\n"
                    f"💵 <b>Сумма:</b> {amount}₽\n"
                    f"🧾 <b>Транзакция:</b> <code>{transaction_id}</code>"
                )
                
                await bot.send_message(ADMIN_CHANNEL, admin_text, parse_mode="HTML")
                print(f"✅ Платёж подтверждён для user {user_id}")
        
        return web.Response(text="OK", status=200)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return web.Response(text="Error", status=500)

app = web.Application()
app.router.add_post('/webhook/platega', platega_webhook)

if __name__ == "__main__":
    print("🚀 Webhook сервер запущен на порту 8081")
    web.run_app(app, host='0.0.0.0', port=8081)
