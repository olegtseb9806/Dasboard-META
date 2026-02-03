# -*- coding: utf-8 -*-
"""
Проверка анкоров напрямую в Google Таблице.
Читает строки с колонками: Page URL, Target URL, Exact Anchor, Found.
Для каждой строки загружает страницу, проверяет наличие ссылки с анкором на целевой URL
и записывает результат (Yes/No/Error) в колонку Found в той же таблице.
"""

import time
import sys
from urllib.parse import urljoin, urlparse

import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup

REQUEST_DELAY = 1.0
TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Названия колонок в таблице (можно поменять под свою таблицу)
COL_PAGE_URL = "Page URL"
COL_TARGET_URL = "Target URL"
COL_EXACT_ANCHOR = "Exact Anchor"
COL_FOUND = "Found"

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def column_letter(n):
    """Номер колонки (1-based) в букву: 1 -> A, 27 -> AA."""
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s or "A"


def normalize_url(url):
    if not url or not str(url).strip():
        return ""
    u = str(url).strip()
    parsed = urlparse(u)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme or 'https'}://{parsed.netloc}{path}{'?' + parsed.query if parsed.query else ''}"


def normalize_anchor(text):
    if text is None:
        return ""
    return " ".join(str(text).split())


def page_contains_anchor_and_link(page_url, target_url, exact_anchor, session):
    target_norm = normalize_url(target_url)
    anchor_norm = normalize_anchor(exact_anchor)

    try:
        r = session.get(page_url, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        return "Error", str(e)

    soup = BeautifulSoup(r.text, "html.parser")
    base_url = r.url

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith("#"):
            continue
        full_href = urljoin(base_url, href).split("#")[0]
        if normalize_url(full_href) != target_norm:
            continue
        if normalize_anchor(a.get_text()) == anchor_norm:
            return "Yes", None

    return "No", "link not found"


def run_checks(sheet_url_or_id, credentials_path=None, sheet_name=None, delay=REQUEST_DELAY):
    """
    sheet_url_or_id: ссылка на таблицу (https://docs.google.com/...) или ID таблицы.
    credentials_path: путь к JSON ключу сервисного аккаунта (по умолчанию — из переменной GOOGLE_APPLICATION_CREDENTIALS или service_account.json в папке скрипта).
    sheet_name: имя листа (если не указано — первый лист).
    """
    creds_path = credentials_path or "service_account.json"
    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    except FileNotFoundError:
        import os
        env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if env_path and os.path.isfile(env_path):
            creds = Credentials.from_service_account_file(env_path, scopes=SCOPE)
        else:
            raise SystemExit(
                "Не найден файл ключа сервисного аккаунта.\n"
                "Положите service_account.json в папку скрипта или укажите путь: python check_anchors_gsheet.py <URL_таблицы> [путь/к/ключу.json]\n"
                "Инструкция по созданию ключа — в README.md"
            )

    gc = gspread.authorize(creds)

    if sheet_url_or_id.startswith("http"):
        sh = gc.open_by_url(sheet_url_or_id)
    else:
        sh = gc.open_by_key(sheet_url_or_id)

    wks = sh.worksheet(sheet_name) if sheet_name else sh.sheet1
    rows = wks.get_all_records()

    if not rows:
        print("В таблице нет данных (или заголовок не совпадает).")
        return

    headers = wks.row_values(1)
    if COL_FOUND not in headers:
        # добавляем колонку Found в конец
        wks.update_acell(1, len(headers) + 1, COL_FOUND)
        headers.append(COL_FOUND)

    col_found_index = headers.index(COL_FOUND) + 1  # 1-based
    col_found_letter = column_letter(col_found_index)

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    results = []
    for i, row in enumerate(rows):
        page_url = (row.get(COL_PAGE_URL) or "").strip() if isinstance(row.get(COL_PAGE_URL), str) else ""
        target_url = (row.get(COL_TARGET_URL) or "").strip() if isinstance(row.get(COL_TARGET_URL), str) else ""
        exact_anchor = (row.get(COL_EXACT_ANCHOR) or "").strip() if isinstance(row.get(COL_EXACT_ANCHOR), str) else str(row.get(COL_EXACT_ANCHOR) or "").strip()

        if not page_url or not target_url:
            result = "Error"
            print(f"  [{i+1}/{len(rows)}] Пропуск: нет Page URL или Target URL")
        else:
            result, detail = page_contains_anchor_and_link(
                page_url, target_url, exact_anchor, session
            )
            if detail:
                print(f"  [{i+1}/{len(rows)}] {page_url[:50]}... -> {result} ({detail})")
            else:
                print(f"  [{i+1}/{len(rows)}] {page_url[:50]}... -> {result}")

        results.append([result])
        if delay and i < len(rows) - 1:
            time.sleep(delay)

    # запись колонки Found в таблицу (начиная со 2-й строки)
    start_cell = f"{col_found_letter}2"
    end_cell = f"{col_found_letter}{len(results) + 1}"
    wks.update(f"{start_cell}:{end_cell}", results, value_input_option="USER_ENTERED")

    print(f"\nГотово. В таблице «{sh.title}» колонка Found обновлена ({len(results)} строк).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Использование: python check_anchors_gsheet.py <URL_или_ID_таблицы> [путь/к/service_account.json] [имя_листа]\n"
            "Пример: python check_anchors_gsheet.py \"https://docs.google.com/spreadsheets/d/ABC123.../edit\""
        )
        sys.exit(1)

    sheet_ref = sys.argv[1].strip()
    creds_path = sys.argv[2].strip() if len(sys.argv) > 2 else None
    sheet_name = sys.argv[3].strip() if len(sys.argv) > 3 else None
    run_checks(sheet_ref, credentials_path=creds_path, sheet_name=sheet_name)
