import os
import sys
import importlib
import traceback

REQUIRED_FILES = [
    "main.py",
    "requirements.txt",
    "bot/__init__.py",
    "bot/main.py",
    "bot/config.py",
    "bot/models.py",
    "bot/db.py",
    "bot/handlers",
]

REQUIRED_MODULES = [
    ("aiogram", "3.13.1"),
    ("python-dotenv", "1.0.1"),
    ("SQLAlchemy", "2.0.30"),
]

def check_files():
    print("\n=== 🔍 Проверка файлов ===")
    missing = []
    for f in REQUIRED_FILES:
        if not os.path.exists(f):
            missing.append(f)
    if missing:
        print("❌ Нет файлов:")
        for m in missing:
            print("   -", m)
    else:
        print("✅ Все нужные файлы на месте")

def check_requirements():
    print("\n=== 📦 Проверка requirements.txt ===")
    if not os.path.exists("requirements.txt"):
        print("❌ Файл отсутствует")
        return

    content = open("requirements.txt").read().strip().splitlines()
    print("Содержимое requirements.txt:")
    for line in content:
        print("  ", line)

def check_imports():
    print("\n=== 📥 Проверка импортов ===")
    for module, needed in REQUIRED_MODULES:
        try:
            mod = importlib.import_module(module)
            print(f"✅ {module} установлен")
        except Exception as e:
            print(f"❌ {module} НЕ установлен:", e)

def check_aiogram_import():
    print("\n=== 🤖 Проверка aiogram ===")
    try:
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
        print("✅ Aiogram 3.x импортируется корректно")
    except Exception as e:
        print("❌ Ошибка aiogram:", e)

def check_main():
    print("\n=== ▶️ Проверка main.py ===")
    try:
        import main
        print("⚠️ main.py импортирован (но запуск не выполнялся)")
    except Exception as e:
        print("❌ Ошибка при импорте main.py:")
        traceback.print_exc()

def run_all():
    check_files()
    check_requirements()
    check_imports()
    check_aiogram_import()
    check_main()

if __name__ == "__main__":
    run_all()
