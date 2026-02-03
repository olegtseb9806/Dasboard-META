# -*- coding: utf-8 -*-
"""
Запуск дашборда из корня проекта (избегает ошибки «app is not a package»).
Запуск: python run_dashboard.py
"""
import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    app_path = root / "app" / "dashboard" / "app.py"
    if not app_path.exists():
        print("Ошибка: не найден app/dashboard/app.py")
        sys.exit(1)
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.headless", "true"],
        cwd=str(root),
    )

if __name__ == "__main__":
    main()
