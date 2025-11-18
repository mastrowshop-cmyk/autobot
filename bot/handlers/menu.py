from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💸 Денежные переводы")],
        [KeyboardButton(text="🟦 Пополнение Alipay")],
        [KeyboardButton(text="🧾 Оплата сервиса")],
        [KeyboardButton(text="📋 Меню менеджера")],
        [KeyboardButton(text="Вход менеджера")],
    ],
    resize_keyboard=True,
)


@router.message()
async def show_menu(m: Message):
    await m.answer("Главное меню", reply_markup=main_menu)
