# -*- coding: utf-8 -*-
"""
Готовит текст для вставки в Streamlit Cloud → Settings → Secrets.
Запуск: python prepare_streamlit_secret.py
Скопируй весь вывод и вставь в поле Secrets.
"""
import json
from pathlib import Path

folder = Path(__file__).resolve().parent
for name in ("service_account.json", "service_account.json.json"):
    p = folder / name
    if p.exists():
        break
else:
    print("Файл service_account.json (или .json.json) не найден в папке проекта.")
    exit(1)

try:
    raw = p.read_text(encoding="utf-8")
    data = json.loads(raw)
except Exception as e:
    print(f"Ошибка чтения JSON: {e}")
    exit(1)

# В TOML значение в тройных кавычках может содержать переносы и кавычки.
# Минифицируем JSON в одну строку, чтобы не было проблем с экранированием.
json_one_line = json.dumps(data, ensure_ascii=False)
print("Скопируй всё ниже (от service_account_json до последней кавычки) и вставь в Streamlit Cloud → Settings → Secrets:\n")
print("service_account_json = '''" + json_one_line + "'''")
