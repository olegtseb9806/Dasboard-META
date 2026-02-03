# -*- coding: utf-8 -*-
"""Печатает email из service_account.json — его нужно добавить в «Поделиться» в каждой из 4 таблиц."""
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
p = folder / "service_account.json"
if not p.exists():
    p = folder / "service_account.json.json"  # двойное расширение в Windows
if not p.exists():
    print("Файл service_account.json не найден в папке проекта.")
    print("Создай сервисный аккаунт в Google Cloud → Keys → JSON → сохрани как service_account.json сюда.")
    exit(1)
try:
    data = json.loads(p.read_text(encoding="utf-8"))
    email = data.get("client_email")
    if email:
        print("Этот email добавь в «Поделиться» в каждой из 4 таблиц (право «Читатель»):")
        print()
        print(email)
        print()
        print("Таблицы:")
        print("  1. https://docs.google.com/spreadsheets/d/1DaiRFqU2d_85cXr0fDmyhzIY4V9fm0zxh4KraZMOFnw/edit")
        print("  2. https://docs.google.com/spreadsheets/d/1v_cheF0k0UCl9CniUWu-pTTYbl0CIOjE0BH0rzW3HXE/edit")
        print("  3. https://docs.google.com/spreadsheets/d/1S5lk-ya4iWwq5znY_vebAuTqloyTlWTcsNuXydZXT00/edit")
        print("  4. https://docs.google.com/spreadsheets/d/1yj3eWqTpjxZFU0e9yg5A6TIh79N-s9g1Zmz3U-Q_54E/edit")
    else:
        print("В файле нет client_email.")
except Exception as e:
    print(f"Ошибка: {e}")
