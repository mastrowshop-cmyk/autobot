from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select

from ..models import Manager, Status, Role
from ..config import load_config

router = Router()
cfg = load_config()


def manager_menu_entry_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📋 Меню менеджера")]],
        resize_keyboard=True,
    )


@router.message(F.text == "Вход менеджера")
async def manager_login_start(m: Message):
    await m.answer("Введите секретный код менеджера:")


@router.message(F.text.func(lambda t: isinstance(t, str) and t.strip() != ""))
async def manager_login_complete(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict):
    # если это не код — игнорируем, обработают другие хендлеры
    if m.text.strip() != cfg.manager_secret_code:
        return

    result = await db.execute(select(Manager).where(Manager.tg_user_id == m.from_user.id))
    mgr = result.scalar_one_or_none()

    if not mgr:
        mgr = Manager(
            first_name=m.from_user.full_name or "Без имени",
            tg_user_id=m.from_user.id,
            role=Role.manager,
            status=Status.online,
        )
    else:
        mgr.status = Status.online

    db.add(mgr)
    await db.commit()
    await db.refresh(mgr)

    sessions[m.from_user.id] = mgr.id
    active_dialogs[mgr.id] = None
    active_orders[mgr.id] = None

    await m.answer(
        f"Привет, {mgr.first_name}! Ты вошёл как {mgr.role.value}.",
        reply_markup=manager_menu_entry_kb(),
    )


@router.message(F.text == "/logout")
async def logout(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict):
    manager_id = sessions.pop(m.from_user.id, None)
    if not manager_id:
        return await m.answer("Ты не авторизован как менеджер.")

    mgr = await db.get(Manager, manager_id)
    if mgr:
        mgr.status = Status.offline
        db.add(mgr)
        await db.commit()

    active_dialogs.pop(manager_id, None)
    active_orders.pop(manager_id, None)

    await m.answer("Ты вышел из системы менеджера.")


@router.message(F.text == "/whoami")
async def whoami(m: Message, db, sessions: dict):
    result = await db.execute(select(Manager).where(Manager.tg_user_id == m.from_user.id))
    mgr = result.scalar_one_or_none()

    if not mgr:
        return await m.answer("Ты не менеджер. Для входа нажми «Вход менеджера» и введи код.")

    await m.answer(
        f"Ты: {mgr.first_name}\n"
        f"Роль: {mgr.role.value}\n"
        f"Статус: {mgr.status.value}"
    )
