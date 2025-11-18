from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from ..models import Manager, Client, Status, Order, OrderStatus

router = Router()


def get_manager_id(user_id: int, sessions: dict) -> int | None:
    return sessions.get(user_id)


@router.message(F.text == "📋 Меню менеджера")
async def menu(m: Message, sessions: dict):
    mid = get_manager_id(m.from_user.id, sessions)
    if not mid:
        return await m.answer("Сначала войди как менеджер: нажми «Вход менеджера» и введи секретный код.")

    text = (
        "📋 МЕНЮ МЕНЕДЖЕРА\n\n"
        "👥 /my_clients – мои клиенты\n"
        "💬 /chat <client_id> – начать диалог\n"
        "📦 /set_order <order_id> <amount> <currency> <описание> – задать параметры заказа\n"
        "🔁 /transfer <client_id> <manager_id> – передать клиента\n\n"
        "Статус:\n"
        "🟢 /online – онлайн\n"
        "🔴 /busy – занят\n"
        "⚫ /offline – оффлайн\n"
    )

    await m.answer(text)


@router.message(F.text.in_({"/online", "/busy", "/offline"}))
async def change_status(m: Message, db, sessions: dict):
    mid = get_manager_id(m.from_user.id, sessions)
    if not mid:
        return await m.answer("Сначала войди как менеджер через «Вход менеджера».")

    mgr = await db.get(Manager, mid)
    if not mgr:
        return await m.answer("Профиль не найден. Обратись к админу.")

    if m.text == "/online":
        mgr.status = Status.online
    elif m.text == "/busy":
        mgr.status = Status.busy
    elif m.text == "/offline":
        mgr.status = Status.offline

    db.add(mgr)
    await db.commit()

    await m.answer(f"Статус обновлён: {mgr.status.value}")


@router.message(F.text == "/my_clients")
async def my_clients(m: Message, db, sessions: dict):
    mid = get_manager_id(m.from_user.id, sessions)
    if not mid:
        return await m.answer("Сначала войди как менеджер.")

    result = await db.execute(select(Client).where(Client.manager_id == mid).order_by(Client.id.asc()))
    clients = result.scalars().all()

    if not clients:
        return await m.answer("У тебя пока нет закреплённых клиентов.")

    lines = ["👥 Твои клиенты:"]
    for c in clients:
        uname = f"@{c.username}" if c.username else ""
        lines.append(f"#{c.id} {uname} (tg_id={c.tg_id})")

    lines.append("")
    lines.append("Чтобы начать писать клиенту: /chat <id>")
    await m.answer("\n".join(lines))


@router.message(F.text.regexp(r"^/chat "))
async def select_client(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict):
    mid = get_manager_id(m.from_user.id, sessions)
    if not mid:
        return await m.answer("Сначала войди как менеджер.")

    parts = m.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await m.answer("Использование: /chat <client_id>")

    client_id = int(parts[1])
    client = await db.get(Client, client_id)
    if not client:
        return await m.answer("Клиент не найден.")

    if client.manager_id != mid:
        return await m.answer("Этот клиент не закреплён за тобой.")

    active_dialogs[mid] = client.id

    result = await db.execute(
        select(Order)
        .where(
            Order.client_id == client.id,
            Order.manager_id == mid,
            Order.status == OrderStatus.active,
        )
        .order_by(Order.created_at.desc())
    )
    order = result.scalar_one_or_none()
    active_orders[mid] = order.id if order else None

    uname = f"@{client.username}" if client.username else ""
    await m.answer(
        f"Теперь все твои сообщения будут уходить клиенту #{client.id} {uname}.\n"
        f"Чтобы сменить клиента – снова /chat <id>."
    )


@router.message(F.text.regexp(r"^/set_order "))
async def set_order(m: Message, db, sessions: dict):
    mid = get_manager_id(m.from_user.id, sessions)
    if not mid:
        return await m.answer("Сначала войди как менеджер.")

    parts = m.text.strip().split()
    if len(parts) < 5:
        return await m.answer("Использование: /set_order <order_id> <amount> <currency> <описание>")

    if not parts[1].isdigit():
        return await m.answer("order_id должен быть числом.")

    order_id = int(parts[1])
    try:
        amount = float(parts[2].replace(",", "."))
    except ValueError:
        return await m.answer("Сумма должна быть числом.")

    currency = parts[3].upper()
    service_desc = " ".join(parts[4:])

    order = await db.get(Order, order_id)
    if not order:
        return await m.answer("Заказ не найден.")

    if order.manager_id != mid:
        return await m.answer("Этот заказ не относится к тебе.")

    order.amount = amount
    order.currency = currency
    order.service_desc = service_desc

    db.add(order)
    await db.commit()

    await m.answer(f"Параметры заказа {order.order_number or order.id} обновлены.")


@router.message(F.text.regexp(r"^/transfer "))
async def transfer_client(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict, bot):
    mid = get_manager_id(m.from_user.id, sessions)
    if not mid:
        return await m.answer("Сначала войди как менеджер.")

    parts = m.text.strip().split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return await m.answer("Использование: /transfer <client_id> <manager_id>")

    client_id = int(parts[1])
    target_mid = int(parts[2])

    client = await db.get(Client, client_id)
    if not client:
        return await m.answer("Клиент не найден.")

    if client.manager_id != mid:
        return await m.answer("Этот клиент не закреплён за тобой.")

    target_mgr = await db.get(Manager, target_mid)
    if not target_mgr or not target_mgr.tg_user_id:
        return await m.answer("Целевой менеджер не найден или не привязан к Telegram.")

    client.manager_id = target_mid
    db.add(client)

    if active_dialogs.get(mid) == client_id:
        active_dialogs[mid] = None
    active_dialogs[target_mid] = None

    await db.commit()

    await m.answer(f"Клиент #{client.id} передан менеджеру {target_mid}.")
    await bot.send_message(
        chat_id=target_mgr.tg_user_id,
        text=f"Тебе передан клиент #{client.id}. Чтобы начать диалог: /chat {client.id}",
    )


@router.message()
async def manager_chat(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict, bot):
    """Обычные сообщения менеджера -> пересылка клиенту."""
    mid = get_manager_id(m.from_user.id, sessions)
    if not mid:
        return

    client_id = active_dialogs.get(mid)
    if not client_id:
        return await m.answer("Сначала выбери клиента командой /chat <id>.")

    client = await db.get(Client, client_id)
    if not client:
        return await m.answer("Клиент не найден. Обнови список: /my_clients.")

    try:
        await bot.copy_message(
            chat_id=client.tg_id,
            from_chat_id=m.chat.id,
            message_id=m.message_id,
        )
    except Exception as e:
        await m.answer(f"Не удалось отправить клиенту: {e}")
