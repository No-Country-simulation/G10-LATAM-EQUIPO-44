@echo off
setlocal EnableExtensions DisableDelayedExpansion
rem Agregado por Edil: web y API locales, sin exponer puertos ni activar Tailscale.
set "EDIL_ROOT=%~dp0"
set "EDIL_PYTHON=%EDIL_ROOT%mediflow\backend\.venv\Scripts\python.exe"
if not exist "%EDIL_PYTHON%" (
    echo ERROR: Falta el entorno Python de mediflow\backend\.venv.
    exit /b 1
)
echo MediFlow local: http://127.0.0.1:8787/web/auditoria/index.html
echo API local:      http://127.0.0.1:8787/docs
echo Tailscale solo da acceso a la red. Los auditores usan usuario y contrasena
echo propios de MediFlow. La primera cuenta se crea con el comando documentado.
echo Este BAT no activa Tailscale ni publica el servicio. Detener con Ctrl+C.
"%EDIL_PYTHON%" "%EDIL_ROOT%mediflow\frontend_web\tool\presentation_server.py" --port 8787 --enable-approved-reviews
exit /b %errorlevel%
