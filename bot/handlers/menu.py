from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select
from datetime import datetime

from ..models import Client, Direction, Order, OrderStatus, Manager
from .client import get_or_create_client, assign_manager

router = Router()

BTN_TRANSFERS = "Денежные переводы"
BTN_ALIPAY = "Пополнение Alipay"
BTN_SERVICE = "Оплата сервиса"
BTN_CONTACT = "Связаться с менеджером"
BTN_CHANGE_DIRECTION = "Изменить направление"
BTN_FINISH_ORDER = "Завершить заказ"
BTN_MANAGER_LOGIN = "Вход менеджера"


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TRANSFERS)],
            [KeyboardButton(text=BTN_ALIPAY)],
            [KeyboardButton(text=BTN_SERVICE)],
            [KeyboardButton(text=BTN_MANAGER_LOGIN)],
        ],
        resize_keyboard=True,
    )


def contact_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CONTACT)],
            [KeyboardButton(text=BTN_CHANGE_DIRECTION)],
        ],
        resize_keyboard=True,
    )


def in_order_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_FINISH_ORDER)]],
        resize_keyboard=True,
    )


def build_order_number(order_id: int, created_at: datetime) -> str:
    year = created_at.year
    return f"OP-{year}-{order_id:05d}"


@router.message(F.text == "/start")
async def start_cmd(m: Message, db):
    client = await get_or_create_client(db, m.from_user)
    client.current_direction = None
    db.add(client)
    await db.commit()

    await m.answer(
        "Привет! 👋\n"
        "Выберите направление, по которому хотите получить помощь:",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text.in_({BTN_TRANSFERS, BTN_ALIPAY, BTN_SERVICE}))
async def choose_direction(m: Message, db):
    from ..models import Direction as Dir

    client = await get_or_create_client(db, m.from_user)

    text = m.text
    if text == BTN_TRANSFERS:
        direction = Dir.transfers
    elif text == BTN_ALIPAY:
        direction = Dir.alipay
    else:
        direction = Dir.service

    client.current_direction = direction
    db.add(client)
    await db.commit()

    await m.answer(
        f"Вы выбрали направление: {text}.\n\n"
        f"Когда будете готовы — нажмите кнопку «{BTN_CONTACT}».",
        reply_markup=contact_kb(),
    )


@router.message(F.text == BTN_CHANGE_DIRECTION)
async def change_direction(m: Message, db):
    client = await get_or_create_client(db, m.from_user)
    client.current_direction = None
    db.add(client)
    await db.commit()

    await m.answer(
        "Хорошо, выберите направление ещё раз:",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == BTN_CONTACT)
async def contact_manager(m: Message, db, bot, active_dialogs: dict, active_orders: dict):
    client = await get_or_create_client(db, m.from_user)

    if not client.current_direction:
        return await m.answer("Сначала выберите направление через /start.")

    result = await db.execute(
        select(Order)
        .where(
            Order.client_id == client.id,
            Order.status == OrderStatus.active,
        )
        .order_by(Order.created_at.desc())
    )
    existing = result.scalar_one_or_none()
    if existing:
        return await m.answer(
            "У вас уже есть активный заказ. Можете продолжать общение с вашим менеджером.",
            reply_markup=in_order_kb(),
        )

    manager = await assign_manager(db)
    if not manager or not manager.tg_user_id:
        return await m.answer("Сейчас нет свободных менеджеров. Попробуйте немного позже 🙏")

    client.manager_id = manager.id
    db.add(client)
    await db.commit()

    order = Order(
        client_id=client.id,
        manager_id=manager.id,
        direction=client.current_direction,
        status=OrderStatus.active,
        created_at=datetime.utcnow(),
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    order.order_number = build_order_number(order.id, order.created_at)
    db.add(order)
    await db.commit()

    active_dialogs[manager.id] = client.id
    active_orders[manager.id] = order.id

    direction_text_map = {
        Direction.transfers: "Денежные переводы",
        Direction.alipay: "Пополнение Alipay",
        Direction.service: "Оплата сервиса",
    }
    dir_text = direction_text_map[client.current_direction]
    uname = f"@{client.username}" if client.username else ""

    await bot.send_message(
        chat_id=manager.tg_user_id,
        text=(
            f"🆕 Новый заказ {order.order_number}\n"
            f"Клиент #{client.id} {uname}\n"
            f"Направление: {dir_text}\n\n"
            f"Чтобы начать писать клиенту: /chat {client.id}\n"
            f"Когда закончите — договоритесь с клиентом и закройте заказ командой «{BTN_FINISH_ORDER}»."
        ),
    )

    await m.answer(
        f"Ваш менеджер: {manager.first_name} 👨‍💼\n"
        f"Номер вашего заказа: {order.order_number}\n"
        f"Можете описать ваш запрос, он всё получит.\n\n"
        f"Когда всё будет решено — нажмите «{BTN_FINISH_ORDER}».",
        reply_markup=in_order_kb(),
    )


@router.message(F.text == BTN_FINISH_ORDER)
async def finish_order(m: Message, db, sessions: dict, active_dialogs: dict, active_orders: dict, bot):
    from ..models import Manager  # локальный импорт

    client = (
        await db.execute(select(Client).where(Client.tg_id == m.from_user.id))
    ).scalar_one_or_none()
    if client:
        if not client.manager_id:
            return await m.answer("У вас нет активного заказа.")

        manager = await db.get(Manager, client.manager_id)

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
            return await m.answer("Активный заказ не найден.")

        order.status = OrderStatus.closed
        order.closed_at = datetime.utcnow()
        client.manager_id = None

        db.add(order)
        db.add(client)
        await db.commit()

        if manager.id in active_dialogs and active_dialogs[manager.id] == client.id:
            active_dialogs[manager.id] = None
        if manager.id in active_orders and active_orders[manager.id] == order.id:
            active_orders[manager.id] = None

        await m.answer(
            "Заказ завершён ✅\n"
            "Спасибо! Если понадобится что-то ещё — напишите /start.",
            reply_markup=main_menu_kb(),
        )
        if manager and manager.tg_user_id:
            await bot.send_message(
                chat_id=manager.tg_user_id,
                text=f"Заказ {order.order_number} завершён клиентом ✅",
            )
        return

    mid = sessions.get(m.from_user.id)
    if not mid:
        return await m.answer("У тебя нет активного заказа или ты не авторизован как менеджер.")

    manager = await db.get(Manager, mid)

    order_id = active_orders.get(manager.id)
    if not order_id:
        return await m.answer("У тебя нет активного заказа.")

    order = await db.get(Order, order_id)
    if not order or order.status != OrderStatus.active:
        return await m.answer("Активный заказ не найден.")

    client = await db.get(Client, order.client_id)

    order.status = OrderStatus.closed
    order.closed_at = datetime.utcnow()
    if client and client.manager_id == manager.id:
        client.manager_id = None

    db.add(order)
    if client:
        db.add(client)
    await db.commit()

    active_orders[manager.id] = None
    active_dialogs[manager.id] = None

    await m.answer(f"Заказ {order.order_number} завершён ✅")
    if client:
        await bot.send_message(
            chat_id=client.tg_id,
            text=(
                "Ваш заказ завершён менеджером ✅\n"
                "Если понадобится ещё помощь — напишите /start."
            ),
            reply_markup=main_menu_kb(),
        )
