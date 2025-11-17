from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select, func

from ..models import Manager, Client, Order, OrderStatus, Role
from ..config import load_config

router = Router()
cfg = load_config()


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Менеджеры"), KeyboardButton(text="📋 Активные заказы")],
            [KeyboardButton(text="📊 Аналитика")],
        ],
        resize_keyboard=True,
    )


async def is_admin(message: Message, db) -> bool:
    # супер-админ по ID
    if message.from_user.id == cfg.superadmin_id:
        return True

    # или менеджер с ролью admin/superadmin
    result = await db.execute(select(Manager).where(Manager.tg_user_id == message.from_user.id))
    mgr = result.scalar_one_or_none()
    if mgr and mgr.role in (Role.admin, Role.superadmin):
        return True

    return False


@router.message(F.text == "/admin")
async def admin_menu(m: Message, db):
    if not await is_admin(m, db):
        return await m.answer("Нет доступа. Эта команда только для админов.")

    await m.answer("👑 Админ-панель", reply_markup=admin_menu_kb())


@router.message(F.text == "👥 Менеджеры")
async def admin_managers(m: Message, db):
    if not await is_admin(m, db):
        return

    result = await db.execute(select(Manager).order_by(Manager.id.asc()))
    managers = result.scalars().all()

    if not managers:
        return await m.answer("Менеджеров пока нет.")

    lines = ["👥 Менеджеры:"]
    for mgr in managers:
        lines.append(
            f"{mgr.id}. {mgr.first_name} — роль: {mgr.role.value}, статус: {mgr.status.value}, tg_id={mgr.tg_user_id}"
        )

    await m.answer("\n".join(lines))


@router.message(F.text == "📋 Активные заказы")
async def admin_active_orders(m: Message, db):
    if not await is_admin(m, db):
        return

    result = await db.execute(
        select(Order).where(Order.status == OrderStatus.active).order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()

    if not orders:
        return await m.answer("Активных заказов нет.")

    lines = ["📋 Активные заказы:"]
    for o in orders:
        lines.append(
            f"{o.order_number or o.id}: клиент #{o.client_id}, менеджер #{o.manager_id}, "
            f"направление: {o.direction.value}, сумма: {float(o.amount) if o.amount else 0} {o.currency or ''}"
        )

    await m.answer("\n".join(lines))


@router.message(F.text == "📊 Аналитика")
async def admin_analytics(m: Message, db):
    if not await is_admin(m, db):
        return

    total_clients = (await db.execute(select(func.count(Client.id)))).scalar_one()
    total_managers = (await db.execute(select(func.count(Manager.id)))).scalar_one()
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar_one()
    total_active = (await db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.active))).scalar_one()
    total_closed = (await db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.closed))).scalar_one()
    total_amount = (await db.execute(select(func.coalesce(func.sum(Order.amount), 0)))).scalar_one()

    text = (
        "📊 Аналитика:
"
        f"Клиентов всего: {total_clients}
"
        f"Менеджеров всего: {total_managers}
"
        f"Заказов всего: {total_orders}
"
        f"Активных заказов: {total_active}
"
        f"Закрытых заказов: {total_closed}
"
        f"Сумма по всем заказам: {float(total_amount):.2f}
"
    )
    await m.answer(text)
