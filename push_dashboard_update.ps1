# Коммит и пуш обновления дашборда (только 2 таблицы)
# Запуск: в PowerShell из корня проекта: .\push_dashboard_update.ps1
# Или: правый клик по файлу -> Run with PowerShell

Set-Location $PSScriptRoot

if (Test-Path .git\index.lock) {
    Remove-Item -Force .git\index.lock
}

git add app/dashboard/app.py app/dashboard/charts.py app/dashboard/data_loader.py app/dashboard/aggregates.py
git status
git commit -m "Dashboard: fix chart labels (annotations), include charts.py in deploy"
if ($LASTEXITCODE -eq 0) {
    git push
}
