import re
import aiohttp
from config import TON_API


class TonChecker:
    @staticmethod
    def is_valid_address(address):
        """Проверка формата TON адреса"""
        if not address:
            return False

        # Проверка формата
        patterns = [
            r'^[a-zA-Z0-9_-]{48}$',  # Базовый адрес
            r'^[a-zA-Z0-9_-]{48}.*$',  # С тегом/мемо
        ]

        for pattern in patterns:
            if re.match(pattern, address):
                return True
        return False

    async def check_address_exists(self, address):
        """Проверка существования адреса через TON API"""
        try:
            # Очищаем адрес от тегов/мемо для проверки
            clean_address = address[:48] if len(address) >= 48 else address

            async with aiohttp.ClientSession() as session:
                async with session.get(
                        f'{TON_API}/accounts/{clean_address}'
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('balance', 0) > 0
                    return False
        except:
            return False


ton_checker = TonChecker()
