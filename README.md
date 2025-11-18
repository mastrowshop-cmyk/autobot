# Oplatym CRM Bot (Telegram Admin Panel)

Telegram-CRM бот для Oplatym:

- Клиент пишет в личку боту и выбирает направление:
  - Денежные переводы
  - Пополнение Alipay
  - Оплата сервиса
- Жмёт «Связаться с менеджером» — бот ищет свободного менеджера и создаёт заказ.
- Формат номера заказа: `OP-ГГГГ-00001`.
- У заказа есть поля: сумма, валюта, описание/сервис.
- Менеджеры авторизуются по коду (MANAGER_SECRET_CODE).
- Админ-панель прямо в Telegram (команда /admin).

## Роли

- superadmin — полный контроль (ID задаётся в SUPERADMIN_ID).
- admin — доступ к админ-панели.
- lead — старший менеджер (пока равен admin по правам, можно расширить).
- manager — обычный менеджер.

## Запуск локально

```bash
pip install -r requirements.txt
cp .env.example .env
# заполнить BOT_TOKEN, при необходимости отредактировать SUPERADMIN_ID и MANAGER_SECRET_CODE
python -m bot.main
```

## Переменные окружения

- `BOT_TOKEN` — токен вашего Telegram-бота.
- `DATABASE_URL` — строка подключения к БД (по умолчанию sqlite+aiosqlite:///./oplatym.db).
- `SUPERADMIN_ID` — Telegram ID супер-админа (по умолчанию 7668402802).
- `MANAGER_SECRET_CODE` — секретный код входа менеджеров (по умолчанию "Nikola").
