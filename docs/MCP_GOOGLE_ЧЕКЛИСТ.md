# MCP Google — что уже сделано и что осталось

## Уже сделано

- **Папка `.config`** создана: `C:\Users\Алежа\.config`
- **MCP-сервер** распакован в: `c:\project\google_workspace_mcp`
- **Зависимости** устанавливались (`python -m pip install .`). Если при первом запуске MCP в Cursor будет ошибка про модуль — открой терминал и выполни:
  ```powershell
  cd c:\project\google_workspace_mcp
  python -m pip install . --no-warn-script-location
  ```
- **Файл `mcp.json`** создан: `C:\Users\Алежа\.cursor\mcp.json`  
  В нём прописаны: `google_workspace`, путь к `main.py`, `cwd`, `GOOGLE_CLIENT_SECRET_PATH`.

---

## Что нужно сделать тебе

### 1. Google Cloud Console (один раз)

1. Зайди на [Google Cloud Console](https://console.cloud.google.com/).
2. Создай или выбери проект, включи API: **Gmail API**, **Google Calendar API**, **Google Drive API**.
3. **OAuth consent screen** (Экран согласия OAuth):  
   Левое меню → **APIs & Services** → **OAuth consent screen** → настрой приложение, добавь scopes (Gmail, Calendar, Drive — см. полную инструкцию).
4. **OAuth Client ID**:  
   **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID** → тип **Desktop app**, имя например `Cursor MCP` → **Create** → скачай JSON.
5. Сохрани скачанный JSON как:  
   `C:\Users\Алежа\.config\google-oauth-credentials.json`  
   (папка `.config` уже есть).

### 2. Путь к Python в mcp.json (если понадобится)

Если в Cursor в логах MCP будет ошибка вроде «can't open file 'main.py'» или «python not found»:

1. В PowerShell выполни: `where.exe python`
2. Открой `C:\Users\Алежа\.cursor\mcp.json`.
3. В поле `"command"` укажи **полный** путь к `python.exe` (с двойными обратными слешами `\\`).

### 3. Перезапуск Cursor

1. Полностью закрой Cursor (в т.ч. из трея).
2. Запусти Cursor снова.

### 4. Проверка

- **View → Output** → канал **MCP**: не должно быть ошибок про `main.py` или credentials.
- В чате напиши, например: «Покажи последние 5 писем в Gmail».  
  При первом запросе MCP может вернуть ссылку для входа в Google — открой её в браузере и разреши доступ.

---

Полная инструкция: файл **ИНСТРУКЦИЯ_MCP_GOOGLE.md** (у тебя в Downloads или в этом проекте, если скопируешь).
