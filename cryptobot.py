import aiohttp
import json
from config import CRYPTOBOT_TOKEN, CRYPTOBOT_API


class CryptoBot:
    def __init__(self):
        self.token = CRYPTOBOT_TOKEN
        self.base_url = CRYPTOBOT_API

    async def create_invoice(self, amount, currency='RUB', description='Оплата заказа'):
        headers = {
            'Crypto-Pay-API-Token': self.token,
            'Content-Type': 'application/json'
        }

        data = {
            'asset': 'USDT',
            'amount': str(amount),
            'description': description,
            'hidden_message': 'Спасибо за покупку!',
            'paid_btn_name': 'check',
            'paid_btn_url': 'https://t.me/your_bot',
            'payload': json.dumps({'type': 'payment'}),
            'allow_comments': False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f'{self.base_url}/createInvoice',
                    headers=headers,
                    json=data
            ) as response:
                result = await response.json()
                if result.get('ok'):
                    return result['result']
                else:
                    raise Exception(f"CryptoBot error: {result.get('error')}")


cryptobot = CryptoBot()
