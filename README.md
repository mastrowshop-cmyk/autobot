# Oplatym CRM Bot — Full Release

Telegram CRM-бот для компании Oplatym:

- Клиент пишет в ЛС боту
- Выбирает направление:
  - Денежные переводы
  - Пополнение Alipay
  - Оплата сервиса
- Нажимает «Связаться с менеджером»
- Система:
  - выбирает свободного менеджера (online, с наименьшим числом клиентов)
  - создаёт заказ с направлением
  - генерирует номер вида `OP-2025-00001`
  - связывает клиента и менеджера
- Менеджер и клиент общаются через бота
- Есть кнопка «Завершить заказ»
- Есть роли: `superadmin`, `admin`, `lead`, `manager`
- Есть простая web-панель (FastAPI) с аналитикой

## Запуск бота локально

```bash
pip install -r requirements.txt
cp .env.example .env
# заполнить BOT_TOKEN
python -m bot.main
```

## Запуск web-панели

```bash
uvicorn bot.webpanel:app --host 0.0.0.0 --port 8000
```

Доступ к панели:

`GET /stats/summary?token=ADMIN_PANEL_TOKEN` и другие эндпоинты.

## На Bothost.ru

- Код из этого проекта залить в GitHub
- В Bothost:
  - указать репозиторий
  - переменные окружения:
    - `BOT_TOKEN`
    - `DATABASE_URL=sqlite+aiosqlite:///./oplatym.db`
  - команда запуска: `python -m bot.main`
