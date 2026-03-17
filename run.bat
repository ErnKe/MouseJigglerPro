@echo off
cd /d "%~dp0"

:: Kütüphane kontrolü - customtkinter yüklü mü?
python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo Ilk calistirma - kutuphaneler yukleniyor...
    pip install customtkinter pystray pillow keyboard psutil pyautogui >nul 2>&1
)

:: Uygulamayı başlat (konsol tamamen gizli)
start "" /B pythonw mouse_jiggler.py
exit /b
