# -*- coding: utf-8 -*-
"""
Удаляет из Google Таблицы все строки, где в 3-м столбце (Цена) значение больше 200.
Использование:
  python filter_price_rows.py "https://docs.google.com/spreadsheets/d/1RTU_DS-7rK5iQVt5Y_2fGjds69Bv6rR9b8X7ZoL1rR8/edit"
  python filter_price_rows.py 1RTU_DS-7rK5iQVt5Y_2fGjds69Bv6rR9b8X7ZoL1rR8

Таблицу нужно расшарить на email из service_account.json (право «Редактор»).
"""
import re
import sys
import gspread
from google.oauth2.service_account import Credentials

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

PRICE_COLUMN_INDEX = 2  # 3-й столбец (0-based: A=0, B=1, C=2)
MAX_PRICE = 200


def parse_price(raw):
    """Извлекает число из строки цены: 150$, $200.00, 130EUR, £100, 200, $1,200 и т.п."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    # Убираем валюты и лишнее
    s = re.sub(r"[$£€]", "", s, flags=re.I)
    s = re.sub(r"\s*(eur|eur\.?|euro|euros?)\s*", " ", s, flags=re.I)
    s = s.replace(",", "").strip()
    # Оставляем только число (и одну точку)
    s = re.sub(r"[^\d.]", "", s)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def extract_spreadsheet_id(url_or_id):
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", str(url_or_id))
    if m:
        return m.group(1)
    return url_or_id.strip()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    spreadsheet_id = extract_spreadsheet_id(sys.argv[1])
    creds_path = sys.argv[2] if len(sys.argv) > 2 else "service_account.json"
    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    except FileNotFoundError:
        print("Файл service_account.json не найден. Положи ключ в папку проекта и расшарь таблицу на client_email из JSON.")
        sys.exit(1)
    gc = gspread.authorize(creds)
    try:
        sh = gc.open_by_key(spreadsheet_id)
    except Exception as e:
        print("Не удалось открыть таблицу. Проверь ID и что таблица расшарена на client_email из service_account.json:", e)
        sys.exit(1)
    sheet = sh.sheet1
    all_rows = sheet.get_all_values()
    if not all_rows:
        print("Таблица пуста.")
        return
    header = all_rows[0]
    to_keep = [header]
    removed = 0
    for i in range(1, len(all_rows)):
        row = all_rows[i]
        while len(row) <= PRICE_COLUMN_INDEX:
            row.append("")
        raw_price = row[PRICE_COLUMN_INDEX]
        price = parse_price(raw_price)
        if price is not None and price > MAX_PRICE:
            removed += 1
            continue
        to_keep.append(row)
    if removed == 0:
        print("Строк с ценой > 200 не найдено. Таблица не изменена.")
        return
    # Записываем обратно: очищаем и пишем только оставшиеся строки
    sheet.clear()
    sheet.update(range_name="A1", values=to_keep, value_input_option="USER_ENTERED")
    print(f"Удалено строк с ценой > {MAX_PRICE}: {removed}. Оставлено строк (с заголовком): {len(to_keep)}.")


if __name__ == "__main__":
    main()
