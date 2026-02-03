# -*- coding: utf-8 -*-
"""
Проверка страниц на наличие анкора и ссылки.
Читает CSV с колонками: Page URL, Target URL, Exact Anchor, Found.
Для каждой строки загружает Page URL и проверяет, есть ли на странице
ссылка с текстом Exact Anchor на Target URL. Заполняет колонку Found.
"""

import csv
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Задержка между запросами (секунды), чтобы не ддосить сайт
REQUEST_DELAY = 1.0
TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def normalize_url(url):
    """Приводит URL к единому виду для сравнения."""
    if not url or not url.strip():
        return ""
    u = url.strip()
    # убираем trailing slash с пути (кроме корня)
    parsed = urlparse(u)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme or 'https'}://{parsed.netloc}{path}{'?' + parsed.query if parsed.query else ''}"


def normalize_anchor(text):
    """Нормализует текст анкора для сравнения (пробелы, переносы)."""
    if text is None:
        return ""
    return " ".join(str(text).split())


def page_contains_anchor_and_link(page_url, target_url, exact_anchor, session):
    """
    Загружает page_url, ищет на странице ссылку:
    - текст ссылки совпадает с exact_anchor (после нормализации);
    - href совпадает с target_url (после нормализации).
    Возвращает ("Yes", None) или ("No", reason) или ("Error", error_message).
    """
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
        # абсолютный URL
        full_href = urljoin(base_url, href)
        # убираем фрагмент #anchor для сравнения
        full_href = full_href.split("#")[0]
        if normalize_url(full_href) != target_norm:
            continue
        link_text = a.get_text()
        if normalize_anchor(link_text) == anchor_norm:
            return "Yes", None

    return "No", "link not found"


def run(input_path, output_path=None, delay=REQUEST_DELAY):
    if output_path is None:
        output_path = input_path

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    with open(input_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if "Found" not in fieldnames:
            fieldnames.append("Found")
        rows = list(reader)

    if not rows:
        print("Нет строк для проверки.")
        return

    for i, row in enumerate(rows):
        page_url = (row.get("Page URL") or "").strip()
        target_url = (row.get("Target URL") or "").strip()
        exact_anchor = (row.get("Exact Anchor") or "").strip()

        if not page_url or not target_url:
            row["Found"] = "Error"
            print(f"  [{i+1}/{len(rows)}] Пропуск: нет Page URL или Target URL")
            continue

        result, detail = page_contains_anchor_and_link(
            page_url, target_url, exact_anchor, session
        )
        row["Found"] = result
        if detail:
            print(f"  [{i+1}/{len(rows)}] {page_url[:50]}... -> {result} ({detail})")
        else:
            print(f"  [{i+1}/{len(rows)}] {page_url[:50]}... -> {result}")

        if delay and i < len(rows) - 1:
            import time
            time.sleep(delay)

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nГотово. Результаты записаны в: {output_path}")


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "anchors.csv"
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    run(input_file, output_file)
