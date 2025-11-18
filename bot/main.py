import asyncio
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from .config import load_config
from .db import init_db, SessionFactory
from .handlers import all_routers


class DBMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with SessionFactory() as db:
            data["db"] = db
            return await handler(event, data)


class SharedStateMiddleware(BaseMiddleware):
    def __init__(self, bot, sessions, active_dialogs, active_orders):
        super().__init__()
        self.bot = bot
        self.sessions = sessions
        self.active_dialogs = active_dialogs
        self.active_orders = active_orders

    async def __call__(self, handler, event, data):
        data["bot"] = self.bot
        data["sessions"] = self.sessions
        data["active_dialogs"] = self.active_dialogs
        data["active_orders"] = self.active_orders
        return await handler(event, data)


async def on_startup(bot: Bot):
    commands = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="admin", description="Админ-панель"),
        BotCommand(command="whoami", description="Кто я"),
        BotCommand(command="logout", description="Выход менеджера"),
    ]
    await bot.set_my_commands(commands)


async def main():
    cfg = load_config()
    if not cfg.token:
        raise RuntimeError("BOT_TOKEN не задан в окружении.")

    bot = Bot(cfg.token, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())

    sessions: dict[int, int] = {}              # tg_user_id менеджера -> manager_id
    active_dialogs: dict[int, int | None] = {} # manager_id -> client_id
    active_orders: dict[int, int | None] = {}  # manager_id -> order_id

    dp.update.middleware(DBMiddleware())
    dp.update.middleware(SharedStateMiddleware(bot, sessions, active_dialogs, active_orders))

    for r in all_routers:
        dp.include_router(r)

    await init_db()
    await on_startup(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
