import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from .config import load_config
from .db import init_db, Session
from .handlers import all_routers


async def on_startup(bot: Bot):
    commands = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="login", description="Вход менеджера"),
        BotCommand(command="menu", description="Меню менеджера"),
    ]
    await bot.set_my_commands(commands)


async def main():
    cfg = load_config()
    bot = Bot(cfg.token, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    sessions: dict[int, int] = {}              # tg_user_id менеджера -> manager_id
    active_dialogs: dict[int, int | None] = {} # manager_id -> client_id
    active_orders: dict[int, int | None] = {}  # manager_id -> order_id

    @dp.update.outer_middleware()
    class DBMiddleware:
        async def __call__(self, handler, event, data):
            async with Session() as db:
                data["db"] = db
                data["bot"] = bot
                data["sessions"] = sessions
                data["active_dialogs"] = active_dialogs
                data["active_orders"] = active_orders
                return await handler(event, data)

    from .handlers import all_routers as routers
    for r in routers:
        dp.include_router(r)

    await init_db()
    await on_startup(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
