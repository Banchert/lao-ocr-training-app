@echo off
REM Script สำหรับรัน Flask app บน Windows พร้อมตั้งค่า UTF-8

REM ตั้งค่า encoding เป็น UTF-8
chcp 65001 > nul

REM ตั้งค่า environment variables
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM ตรวจสอบว่ามี Python หรือไม่
python --version > nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH!
    pause
    exit /b 1
)

REM สร้างโฟลเดอร์ที่จำเป็น
echo Creating necessary directories...
mkdir templates 2>nul
mkdir static\css 2>nul
mkdir static\js 2>nul
mkdir training_scripts 2>nul
mkdir logs 2>nul
mkdir fonts 2>nul
mkdir corpus 2>nul
mkdir dataset 2>nul
mkdir models 2>nul

REM ติดตั้ง dependencies (ถ้ายังไม่ได้ติดตั้ง)
echo.
echo Checking dependencies...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Installing Flask...
    pip install flask
)

pip show torch >nul 2>&1
if errorlevel 1 (
    echo Installing PyTorch...
    echo Please install PyTorch manually from https://pytorch.org/
    echo For GPU support, choose the appropriate CUDA version
    pause
)

pip show pillow >nul 2>&1
if errorlevel 1 (
    echo Installing Pillow...
    pip install pillow
)

pip show torchvision >nul 2>&1
if errorlevel 1 (
    echo Installing torchvision...
    pip install torchvision
)

REM รัน Flask app
echo.
echo Starting Flask application...
echo Access the application at: http://localhost:5000
echo.
python app.py

pause