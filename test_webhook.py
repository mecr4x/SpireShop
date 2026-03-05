import requests
try:
    response = requests.get('http://localhost:8080/webhook/platega', timeout=5)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {response.text}")
except requests.exceptions.ConnectionError:
    print("❌ Ошибка подключения — сервер не отвечает на порту 8080")
except Exception as e:
    print(f"❌ Ошибка: {e}")
