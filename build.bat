@echo off
py -m pip install --upgrade pip
py -m pip install -r requirements.txt pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name OlympicCCTVViewer main.py
echo.
echo 빌드 완료: dist\OlympicCCTVViewer.exe
pause
