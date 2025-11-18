from aiogram import Router
from aiogram.types import Message
from sqlalchemy import select, func
from datetime import datetime

from ..models import Client, Manager, Status, Order, OrderStatus

router = Router()


async def get_or_create_client(db, tg_user) -> Client:
    result = await db.execute(select(Client).where(Client.tg_id == tg_user.id))
    client = result.scalar_one_or_none()
    if client:
        return client

    client = Client(
        tg_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        created_at=datetime.utcnow(),
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def assign_manager(db) -> Manager | None:
    # Находим онлайн-менеджера с минимальным количеством клиентов
    subq = (
        select(Client.manager_id, func.count(Client.id).label("cnt"))
        .where(Client.manager_id.is_not(None))
        .group_by(Client.manager_id)
        .subquery()
    )

    q = (
        select(Manager)
        .where(Manager.status == Status.online)
        .outerjoin(subq, subq.c.manager_id == Manager.id)
        .order_by(subq.c.cnt.nullsfirst(), Manager.id.asc())
    )

    result = await db.execute(q)
    manager = result.scalar_one_or_none()
    return manager


@router.message()
async def client_message(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict, bot):
    # Если это менеджер — игнорим, это обработает другой хендлер
    if m.from_user.id in sessions:
        return

    client = await get_or_create_client(db, m.from_user)

    if not client.manager_id:
        return await m.answer(
            "Пожалуйста, сначала выберите направление и свяжитесь с менеджером через меню /start."
        )

    manager = await db.get(Manager, client.manager_id)
    if not manager or not manager.tg_user_id:
        return await m.answer(
            "Ваш менеджер временно недоступен. Попробуйте позже или напишите /start."
        )

    result = await db.execute(
        select(Order)
        .where(
            Order.client_id == client.id,
            Order.manager_id == manager.id,
            Order.status == OrderStatus.active,
        )
        .order_by(Order.created_at.desc())
    )
    order = result.scalar_one_or_none()
    if not order:
        return await m.answer("Активный заказ не найден. Нажмите /start, чтобы создать новый.")

    try:
        await bot.copy_message(
            chat_id=manager.tg_user_id,
            from_chat_id=m.chat.id,
            message_id=m.message_id,
        )
    except Exception:
        pass

    await m.answer("Сообщение отправлено вашему менеджеру 👍")
