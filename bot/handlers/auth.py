from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select

from ..models import Manager, Status, Role

router = Router()


@router.message(Command("login"))
async def login(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict):
    parts = m.text.strip().split()
    if len(parts) != 2:
        return await m.answer("Использование: /login <код>")

    code = parts[1]
    result = await db.execute(select(Manager).where(Manager.login_code == code))
    mgr = result.scalar_one_or_none()

    if not mgr:
        return await m.answer("Неверный код. Обратись к старшему.")

    mgr.tg_user_id = m.from_user.id
    mgr.status = Status.online
    db.add(mgr)
    await db.commit()

    sessions[m.from_user.id] = mgr.id
    active_dialogs[mgr.id] = None
    active_orders[mgr.id] = None

    await m.answer(
        f"Привет, {mgr.first_name}! Ты вошёл как {mgr.role.value}.
"
        f"Команда меню: /menu"
    )


@router.message(Command("logout"))
async def logout(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict):
    manager_id = sessions.pop(m.from_user.id, None)
    if not manager_id:
        return await m.answer("Ты не авторизован.")

    mgr = await db.get(Manager, manager_id)
    if mgr:
        mgr.status = Status.offline
        db.add(mgr)
        await db.commit()

    active_dialogs.pop(manager_id, None)
    active_orders.pop(manager_id, None)

    await m.answer("Ты вышел из системы.")


@router.message(Command("whoami"))
async def whoami(m: Message, db, sessions: dict):
    mid = sessions.get(m.from_user.id)
    if not mid:
        return await m.answer("Ты не авторизован. /login <код>")

    mgr = await db.get(Manager, mid)
    if not mgr:
        return await m.answer("Ошибка профиля. Обратись к админу.")

    await m.answer(
        f"Ты: {mgr.first_name}, роль: {mgr.role.value}, статус: {mgr.status.value}"
    )
