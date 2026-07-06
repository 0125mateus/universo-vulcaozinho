@echo off
cd /d "%~dp0"
echo === Universo Vulcãozinho ===
python --version >nul 2>&1 || (
    echo Python nao encontrado. Instale Python 3.12+ e tente novamente.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\activate.bat" (
    echo Criando ambiente virtual...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
python manage.py migrate
echo.
echo Iniciando servidor em http://127.0.0.1:8000/
echo Login demo: recepcao_nacional / vulcaozinho123
echo.
python manage.py runserver
pause
