# http_wrapper.py — обёртка для запуска бота на Bothost
import main

if __name__ == "__main__":
    import asyncio
    asyncio.run(main.main())
