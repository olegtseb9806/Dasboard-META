# Коммит и пуш обновления дашборда (только 2 таблицы)
# Запуск: в PowerShell из корня проекта: .\push_dashboard_update.ps1
# Или: правый клик по файлу -> Run with PowerShell

Set-Location $PSScriptRoot

if (Test-Path .git\index.lock) {
    Remove-Item -Force .git\index.lock
}

git add app/dashboard/app.py app/dashboard/data_loader.py
git status
git commit -m "Dashboard: only 2 tables MR Anchors and TelecomAsia, no table checkboxes"
if ($LASTEXITCODE -eq 0) {
    git push
}
