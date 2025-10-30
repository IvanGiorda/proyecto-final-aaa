@echo off
echo =========================================
echo  Crear Ejecutable de VideoCall App
echo =========================================
echo.

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Instalar PyInstaller
echo Instalando PyInstaller...
pip install pyinstaller
echo.

REM Crear ejecutable
echo Creando ejecutable...
pyinstaller --onefile ^
    --windowed ^
    --name="VideoCallApp" ^
    --icon=icono.ico ^
    --add-data "usuarios.json;." ^
    pruebas2.py

if errorlevel 1 (
    echo [ERROR] Error al crear el ejecutable
    pause
    exit /b 1
)

echo.
echo =========================================
echo  Ejecutable creado exitosamente!
echo =========================================
echo.
echo El ejecutable se encuentra en:
echo   dist\VideoCallApp.exe
echo.
echo Puedes distribuir este archivo junto con usuarios.json
echo.
pause