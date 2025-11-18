from aiogram import Router, F
from aiogram.types import Message

from bot.models import Client, Direction, Order, OrderStatus
from bot.db import get_session
from bot.handlers.auth import sessions

router = Router()

# active_dialogs = { client_id: manager_id }
active_dialogs = {}

# active_orders = { manager_id: order_id }
active_orders = {}


@router.message(F.text.in_({"💸 Денежные переводы", "🟦 Пополнение Alipay", "🧾 Оплата сервиса"}))
async def client_choose_direction(m: Message, db=get_session):
    direction_map = {
        "💸 Денежные переводы": Direction.transfers,
        "🟦 Пополнение Alipay": Direction.alipay,
        "🧾 Оплата сервиса": Direction.service,
    }

    direction = direction_map[m.text]

    async for session in db():
        client = await session.get(Client, m.from_user.id)
        if not client:
            client = Client(
                id=m.from_user.id,
                tg_id=m.from_user.id,
                username=m.from_user.username,
                first_name=m.from_user.first_name,
                last_name=m.from_user.last_name,
                current_direction=direction,
            )
            session.add(client)
        else:
            client.current_direction = direction

        await session.commit()

    await m.answer(
        "Теперь выберите: Связь с менеджером",
    )


@router.message(F.text == "Связь с менеджером")
async def request_manager(m: Message, db=get_session):
    async for session in db():
        client = await session.get(Client, m.from_user.id)
        if not client:
            return await m.answer("Ошибка. Выберите направление сначала.")

        # ищем свободного менеджера
        from bot.models import Manager, Status

        free = await session.execute(
            Manager.__table__.select().where(Manager.status == Status.online)
        )
        free_mgr = free.first()

        if not free_mgr:
            return await m.answer("Нет доступных менеджеров. Попробуйте позже.")

        manager_id = free_mgr.id

        client.manager_id = manager_id
        session.add(client)
        await session.commit()

        # создаём заказ
        order = Order(
            client_id=m.from_user.id,
            manager_id=manager_id,
            direction=client.current_direction,
            status=OrderStatus.active,
        )
        session.add(order)
        await session.commit()

        # уведомляем менеджера
        from bot.main import bot

        await bot.send_message(
            free_mgr.tg_user_id,
            f"🆕 Новый клиент #{client.id}\nНаправление: {client.current_direction.value}\n"
            f"Чтобы начать диалог: /chat {client.id}",
        )

    await m.answer("Менеджер подключается…")
