import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from .config import load_config
from .db import init_db, get_session_middleware
from .handlers import all_routers


async def main():
    cfg = load_config()

    # Новый формат — только так работает в Aiogram 3.7 и выше
    bot = Bot(
        token=cfg.token,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Middleware для БД
    dp.update.middleware(get_session_middleware())

    # Подключаем все роутеры
    for router in all_routers:
        dp.include_router(router)

    # Инициализация базы
    await init_db()

    print("BOT STARTED")

    # Запуск long-polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
