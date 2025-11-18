from aiogram import Router, F
from aiogram.types import Message

from bot.models import Manager, Role
from bot.db import get_session
from bot.config import load_config

router = Router()
cfg = load_config()

# sessions = { telegram_user_id: manager_id }
sessions = {}


@router.message(F.text == "Вход менеджера")
async def start_manager_login(m: Message):
    await m.answer("Введите секретный код менеджера:")


@router.message()
async def manager_login(m: Message, db= get_session):
    text = m.text.strip()

    # superadmin вход
    if text == str(cfg.superadmin_id):
        sessions[m.from_user.id] = -1
        return await m.answer("🔥 Вход супер-админа выполнен.\nПишите /admin")

    # менеджер вход
    if text == cfg.manager_secret_code:
        async for session in db():
            # ищем менеджера по Telegram ID
            manager = await session.get(Manager, m.from_user.id)

            if not manager:
                # создаём, если не существует
                manager = Manager(
                    first_name=m.from_user.first_name or "Менеджер",
                    tg_user_id=m.from_user.id,
                    role=Role.manager,
                )
                session.add(manager)
                await session.commit()

            sessions[m.from_user.id] = manager.id

            return await m.answer(
                f"Успешный вход менеджера!\n"
                f"Ваш ID: {manager.id}\n"
                f"Откройте меню: 📋 Меню менеджера"
            )

    # если ничего не подошло
    await m.answer("❌ Неверный код.")
