from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select, func

from bot.models import Manager, Role, Status, Client, Order, OrderStatus
from bot.db import get_session
from bot.config import load_config
from bot.handlers.auth import sessions

router = Router()
cfg = load_config()


def is_superadmin(user_id: int):
    """Проверка прав."""
    return user_id == cfg.superadmin_id


# =============================
# 🔐 ВХОД В АДМИН-ПАНЕЛЬ
# =============================
@router.message(F.text == "/admin")
async def admin_panel(m: Message):
    if not is_superadmin(m.from_user.id):
        return await m.answer("❌ У вас нет доступа к админ-панели.")

    txt = (
        "⚙️ <b>Админ-панель</b>\n\n"
        "Команды:\n"
        "/managers – список менеджеров\n"
        "/add_manager <имя> – создать менеджера\n"
        "/bind <manager_id> – привязать Telegram менеджеру\n"
        "/analytics – аналитика\n"
    )
    await m.answer(txt)


# =============================
# 👥 СПИСОК МЕНЕДЖЕРОВ
# =============================
@router.message(F.text == "/managers")
async def show_managers(m: Message):
    if not is_superadmin(m.from_user.id):
        return await m.answer("❌ Нет доступа.")

    async for session in get_session():
        result = await session.execute(select(Manager))
        managers = result.scalars().all()

        if not managers:
            return await m.answer("Менеджеров нет.")

        text = ["👥 <b>Менеджеры:</b>\n"]
        for mgr in managers:
            tg = f"TG: {mgr.tg_user_id}" if mgr.tg_user_id else "❌ не привязан"
            text.append(f"ID: {mgr.id} | {mgr.first_name} | {mgr.role} | {tg}")

        await m.answer("\n".join(text))


# =============================
# ➕ ДОБАВИТЬ МЕНЕДЖЕРА
# =============================
@router.message(F.text.regexp(r"^/add_manager "))
async def add_manager(m: Message):
    if not is_superadmin(m.from_user.id):
        return await m.answer("❌ Нет доступа.")

    parts = m.text.split()
    if len(parts) < 2:
        return await m.answer("Использование: /add_manager <имя>")

    name = " ".join(parts[1:])

    async for session in get_session():
        mgr = Manager(
            first_name=name,
            role=Role.manager,
            status=Status.offline,
        )
        session.add(mgr)
        await session.commit()

        await m.answer(f"✅ Менеджер создан.\nID: {mgr.id}\nИмя: {mgr.first_name}")


# =============================
# 🔗 ПРИВЯЗАТЬ TELEGRAM К МЕНЕДЖЕРУ
# =============================
@router.message(F.text.regexp(r"^/bind "))
async def bind_manager(m: Message):
    if not is_superadmin(m.from_user.id):
        return await m.answer("❌ Нет доступа.")

    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.answer("Использование: /bind <manager_id>")

    manager_id = int(parts[1])

    async for session in get_session():
        mgr = await session.get(Manager, manager_id)
        if not mgr:
            return await m.answer("❌ Менеджер не найден.")

        mgr.tg_user_id = m.from_user.id
        session.add(mgr)
        await session.commit()

        await m.answer(f"🔗 Telegram привязан к менеджеру {mgr.first_name} (ID {mgr.id}).")


# =============================
# 📊 АНАЛИТИКА
# =============================
@router.message(F.text == "/analytics")
async def analytics(m: Message):
    if not is_superadmin(m.from_user.id):
        return await m.answer("❌ Нет доступа.")

    async for session in get_session():

        # количество клиентов
        total_clients = await session.execute(select(func.count(Client.id)))
        total_clients = total_clients.scalar() or 0

        # активные заказы
        active_orders = await session.execute(
            select(func.count(Order.id)).where(Order.status == OrderStatus.active)
        )
        active_orders = active_orders.scalar() or 0

        # завершённые заказы
        closed_orders = await session.execute(
            select(func.count(Order.id)).where(Order.status == OrderStatus.closed)
        )
        closed_orders = closed_orders.scalar() or 0

        # менеджеры онлайн
        online = await session.execute(
            select(func.count(Manager.id)).where(Manager.status == Status.online)
        )
        online = online.scalar() or 0

        text = (
            "📊 <b>Аналитика</b>\n\n"
            f"👥 Всего клиентов: <b>{total_clients}</b>\n"
            f"📦 Активных заказов: <b>{active_orders}</b>\n"
            f"✅ Завершённых заказов: <b>{closed_orders}</b>\n"
            f"🟢 Менеджеров онлайн: <b>{online}</b>\n"
        )

        await m.answer(text)

