import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.config import load_config
from bot.handlers import all_routers
from bot.db import init_db


async def main():
    cfg = load_config()

    await init_db()

    bot = Bot(
        token=cfg.token,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()
    dp.include_router(all_routers)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
