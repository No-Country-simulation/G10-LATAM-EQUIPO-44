@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Agregado por Edil: inicia la copia actual del proyecto, sin cambiar ramas ni instalar paquetes.
rem Cada servicio queda en una ventana visible para poder leer errores y detenerlo con Ctrl+C.
set "MEDIFLOW_ROOT=%~dp0"
set "MEDIFLOW_BACKEND=%MEDIFLOW_ROOT%mediflow\backend"
set "MEDIFLOW_WEB=%MEDIFLOW_ROOT%mediflow\frontend_web\src"
set "MEDIFLOW_APP=%MEDIFLOW_ROOT%mediflow\frontend_mobile\mediflow_app"
set "MEDIFLOW_PYTHON=%MEDIFLOW_BACKEND%\.venv\Scripts\python.exe"

if /i "%~1"=="--backend" goto backend
if /i "%~1"=="--web" goto web
if /i "%~1"=="--app" goto app
if not "%~1"=="" if /i not "%~1"=="--check" goto usage

if not exist "%MEDIFLOW_PYTHON%" (
    echo ERROR: No existe el entorno Python: "%MEDIFLOW_PYTHON%"
    echo Crea el entorno en mediflow\backend\.venv e instala mediflow\requirements.txt.
    goto fail
)
if not exist "%MEDIFLOW_BACKEND%\app\main.py" goto missing
if not exist "%MEDIFLOW_WEB%\ingesta\index.html" goto missing
if not exist "%MEDIFLOW_APP%\pubspec.yaml" goto missing
if not exist "%MEDIFLOW_APP%\windows\CMakeLists.txt" (
    echo ERROR: Esta copia no tiene el soporte Windows de Flutter.
    goto fail
)

rem Agregado por Edil: primero PATH, despues FLUTTER_ROOT y la instalacion local conocida.
set "MEDIFLOW_FLUTTER="
for /f "delims=" %%F in ('where flutter.bat 2^>nul') do if not defined MEDIFLOW_FLUTTER set "MEDIFLOW_FLUTTER=%%F"
if not defined MEDIFLOW_FLUTTER if defined FLUTTER_ROOT if exist "%FLUTTER_ROOT%\bin\flutter.bat" set "MEDIFLOW_FLUTTER=%FLUTTER_ROOT%\bin\flutter.bat"
if not defined MEDIFLOW_FLUTTER if exist "D:\flutter\flutter\bin\flutter.bat" set "MEDIFLOW_FLUTTER=D:\flutter\flutter\bin\flutter.bat"
if not defined MEDIFLOW_FLUTTER (
    echo ERROR: No se encontro Flutter. Agregalo a PATH o configura FLUTTER_ROOT.
    goto fail
)

"%MEDIFLOW_PYTHON%" -c "import uvicorn, fastapi, oci, google.genai, pypdf" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Faltan dependencias Python. Ejecuta:
    echo "%MEDIFLOW_PYTHON%" -m pip install -r "%MEDIFLOW_ROOT%mediflow\requirements.txt"
    goto fail
)
if /i "%~1"=="--check" (
    echo OK: Rutas, dependencias Python, Flutter y soporte Windows encontrados.
    echo No se iniciaron servicios ni se probaron credenciales OCI o Gemini.
    exit /b 0
)

rem Agregado por Edil: no iniciar duplicados ni asumir que un puerto ocupado pertenece a MediFlow.
powershell.exe -NoProfile -Command "$ports = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners(); if ($ports.Port -contains 8000 -or $ports.Port -contains 8080) { exit 1 }"
if errorlevel 1 (
    echo ERROR: El puerto 8000 o 8080 esta ocupado, o no se pudo comprobar.
    echo Deten el servidor anterior con Ctrl+C y vuelve a ejecutar este archivo.
    goto fail
)
if not exist "%MEDIFLOW_ROOT%mediflow\.env" (
    echo AVISO: Falta mediflow\.env. El backend puede iniciar, pero OCI y Gemini requieren configuracion local.
)

echo Iniciando MediFlow desde "%MEDIFLOW_ROOT%"
echo Backend: http://127.0.0.1:8000/docs
echo Web:     http://127.0.0.1:8080/ingesta/
rem Codigo anterior: echo La web usa datos de demostracion; no recibe automaticamente los archivos de Flutter.
echo El historial consulta el backend; las otras pantallas web siguen siendo prototipos.
echo Cierra cada servicio con Ctrl+C en su ventana. No se realizan llamadas de prueba a OCI o Gemini.
start "MediFlow - Backend" "%ComSpec%" /d /k ""%~f0" --backend"
start "MediFlow - Web" "%ComSpec%" /d /k ""%~f0" --web"
start "MediFlow - Flutter Windows" "%ComSpec%" /d /k ""%~f0" --app"
exit /b 0

:backend
cd /d "%MEDIFLOW_BACKEND%" || exit /b 1
"%MEDIFLOW_PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
exit /b %errorlevel%

:web
cd /d "%MEDIFLOW_WEB%" || exit /b 1
"%MEDIFLOW_PYTHON%" -m http.server 8080 --bind 127.0.0.1
exit /b %errorlevel%

:app
cd /d "%MEDIFLOW_APP%" || exit /b 1
rem Agregado por Edil: el archivo original ya valida Flutter antes de abrir esta ventana.
rem No activamos Gemini ni enviamos documentos; la app conserva su consentimiento por archivo.
call "%MEDIFLOW_FLUTTER%" pub get
if errorlevel 1 exit /b 1
call "%MEDIFLOW_FLUTTER%" run -d windows --dart-define=API_BASE_URL=http://127.0.0.1:8000
exit /b %errorlevel%

:missing
echo ERROR: Falta una carpeta o archivo del proyecto. Ejecuta el BAT desde una copia completa de MediFlow.
goto fail

:usage
echo Uso: iniciar_mediflow.bat [--check]
exit /b 1

:fail
if /i not "%~1"=="--check" pause
exit /b 1
