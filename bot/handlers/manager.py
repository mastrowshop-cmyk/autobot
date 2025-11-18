from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from bot.models import Manager, Client, Status, Order, OrderStatus
from bot.db import get_session
from bot.handlers.auth import sessions

router = Router()

# active_dialogs = { manager_id: client_id }
active_dialogs = {}

# active_orders = { manager_id: order_id }
active_orders = {}


def get_manager_id(user_id: int):
    """Возвращает id менеджера по Telegram user_id."""
    return sessions.get(user_id)


# ==========================
# 📋 МЕНЮ МЕНЕДЖЕРА
# ==========================
@router.message(F.text == "📋 Меню менеджера")
async def menu(m: Message):
    mid = get_manager_id(m.from_user.id)
    if not mid:
        return await m.answer("Сначала войдите через 'Вход менеджера'.")

    txt = (
        "📋 <b>Меню менеджера</b>\n\n"
        "Команды:\n"
        "/my_clients – список моих клиентов\n"
        "/online – статус онлайн\n"
        "/busy – статус занят\n"
        "/offline – статус оффлайн\n"
        "/chat <id> – открыть чат с клиентом\n"
        "/set_order <id> <сумма> <валюта> <описание>\n"
        "/transfer <client_id> <manager_id> – передать клиента"
    )
    await m.answer(txt)


# ==========================
# 🟢 СМЕНА СТАТУСА
# ==========================
@router.message(F.text.in_({"/online", "/busy", "/offline"}))
async def change_status(m: Message):
    mid = get_manager_id(m.from_user.id)
    if not mid:
        return await m.answer("Сначала войдите как менеджер.")

    async for session in get_session():

        mgr = await session.get(Manager, mid)
        if not mgr:
            return await m.answer("Профиль менеджера не найден.")

        if m.text == "/online":
            mgr.status = Status.online
        elif m.text == "/busy":
            mgr.status = Status.busy
        else:
            mgr.status = Status.offline

        session.add(mgr)
        await session.commit()

        await m.answer(f"Статус обновлён: {mgr.status.value}")


# ==========================
# 👥 СПИСОК МОИХ КЛИЕНТОВ
# ==========================
@router.message(F.text == "/my_clients")
async def my_clients(m: Message):
    mid = get_manager_id(m.from_user.id)
    if not mid:
        return await m.answer("Ты не авторизован как менеджер.")

    async for session in get_session():

        result = await session.execute(
            select(Client).where(Client.manager_id == mid).order_by(Client.id.asc())
        )
        clients = result.scalars().all()

        if not clients:
            return await m.answer("У тебя нет закреплённых клиентов.")

        lines = ["👥 <b>Твои клиенты:</b>"]
        for c in clients:
            uname = f"@{c.username}" if c.username else ""
            lines.append(f"#{c.id} {uname}")

        lines.append("\nЧтобы начать писать клиенту: /chat <id>")
        await m.answer("\n".join(lines))


# ==========================
# 💬 ВЫБОР КЛИЕНТА ДЛЯ ДИАЛОГА
# ==========================
@router.message(F.text.regexp(r"^/chat "))
async def select_client(m: Message):
    mid = get_manager_id(m.from_user.id)
    if not mid:
        return await m.answer("Ты не авторизован.")

    parts = m.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.answer("Использование: /chat <client_id>")

    client_id = int(parts[1])

    async for session in get_session():

        client = await session.get(Client, client_id)
        if not client:
            return await m.answer("Клиент не найден.")

        if client.manager_id != mid:
            return await m.answer("Этот клиент не закреплён за тобой.")

        active_dialogs[mid] = client_id

        # активный заказ менеджера
        result = await session.execute(
            select(Order).where(
                Order.client_id == client_id,
                Order.manager_id == mid,
                Order.status == OrderStatus.active
            )
        )
        order = result.scalar_one_or_none()
        active_orders[mid] = order.id if order else None

        await m.answer(
            f"Теперь все сообщения будут отправляться клиенту #{client_id}.\n"
            f"Чтобы выбрать другого — /chat <id>"
        )


# ==========================
# 📦 УСТАНОВИТЬ ПАРАМЕТРЫ ЗАКАЗА
# ==========================
@router.message(F.text.regexp(r"^/set_order "))
async def set_order(m: Message):
    mid = get_manager_id(m.from_user.id)
    if not mid:
        return await m.answer("Войдите как менеджер.")

    parts = m.text.split()
    if len(parts) < 5:
        return await m.answer("Использование: /set_order <id> <сумма> <валюта> <описание>")

    order_id = int(parts[1])
    try:
        amount = float(parts[2].replace(",", "."))
    except:
        return await m.answer("Сумма должна быть числом.")

    currency = parts[3].upper()
    desc = " ".join(parts[4:])

    async for session in get_session():

        order = await session.get(Order, order_id)
        if not order:
            return await m.answer("Заказ не найден.")

        if order.manager_id != mid:
            return await m.answer("Этот заказ не принадлежит тебе.")

        order.amount = amount
        order.currency = currency
        order.service_desc = desc

        session.add(order)
        await session.commit()

        await m.answer("Параметры заказа обновлены.")


# ==========================
# 🔁 ПЕРЕДАТЬ КЛИЕНТА
# ==========================
@router.message(F.text.regexp(r"^/transfer "))
async def transfer_client(m: Message):
    mid = get_manager_id(m.from_user.id)
    if not mid:
        return await m.answer("Ты не менеджер.")

    parts = m.text.split()
    if len(parts) != 3:
        return await m.answer("Использование: /transfer <client_id> <manager_id>")

    client_id = int(parts[1])
    target_mid = int(parts[2])

    async for session in get_session():

        client = await session.get(Client, client_id)
        if not client:
            return await m.answer("Клиент не найден.")

        if client.manager_id != mid:
            return await m.answer("Этот клиент не твой.")

        new_mgr = await session.get(Manager, target_mid)
        if not new_mgr or not new_mgr.tg_user_id:
            return await m.answer("Целевой менеджер не найден.")

        client.manager_id = target_mid
        session.add(client)
        await session.commit()

        active_dialogs[mid] = None
        active_dialogs[target_mid] = None

        from bot.main import bot
        await bot.send_message(
            new_mgr.tg_user_id,
            f"Тебе передан клиент #{client_id}. Используй /chat {client_id}"
        )

        await m.answer("Клиент передан.")


# ==========================
# ✉️ ОТПРАВКА СООБЩЕНИЙ КЛИЕНТУ
# ==========================
@router.message()
async def manager_message(m: Message):
    mid = get_manager_id(m.from_user.id)
    if not mid:
        return

    client_id = active_dialogs.get(mid)
    if not client_id:
        return await m.answer("Выберите клиента: /chat <id>")

    async for session in get_session():

        client = await session.get(Client, client_id)
        if not client:
            return await m.answer("Клиент не найден.")

        from bot.main import bot
        await bot.copy_message(
            chat_id=client.tg_id,
            from_chat_id=m.chat.id,
            message_id=m.message_id,
        )
