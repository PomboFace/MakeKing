@echo off
echo ============================
echo   Building MakeKing (Web)
echo ============================

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

pygbag ^
    --build ^
    --archive ^
    --app_name MakeKing ^
    --icon assets/sprites/icon.png ^
    MakeKing.py

echo ============================
echo   Build Complete
echo ============================

cd build\web
start python -m http.server 8000
timeout /t 1 >nul
start "" http://localhost:8000

pause