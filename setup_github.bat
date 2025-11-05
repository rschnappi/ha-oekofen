@echo off
echo ===============================================
echo  ÖkOfen GitHub Repository Setup
echo ===============================================
echo.

echo [1/6] Git Repository initialisieren...
git init
if %ERRORLEVEL% neq 0 (
    echo FEHLER: Git init fehlgeschlagen. Ist Git installiert?
    pause
    exit /b 1
)

echo [2/6] Remote Repository hinzufügen...
git remote add origin https://github.com/rschnappi/ha-oekofen.git
if %ERRORLEVEL% neq 0 (
    echo WARNUNG: Remote bereits vorhanden oder Fehler beim Hinzufügen
)

echo [3/6] Alle Dateien zum Staging hinzufügen...
git add .
if %ERRORLEVEL% neq 0 (
    echo FEHLER: Git add fehlgeschlagen
    pause
    exit /b 1
)

echo [4/6] Initial commit erstellen...
git commit -m "Initial commit: ÖkOfen Pellematic Home Assistant Integration

- Complete Home Assistant custom component
- Support for multiple temperature sensors
- Boiler status monitoring  
- Pump status monitoring
- Error count tracking
- Multi-language support (DE/EN)
- Debug mode for development
- Configurable update intervals
- Based on Pellematic web interface API"

if %ERRORLEVEL% neq 0 (
    echo FEHLER: Git commit fehlgeschlagen
    pause
    exit /b 1
)

echo [5/6] Branch zu main umbenennen...
git branch -M main
if %ERRORLEVEL% neq 0 (
    echo WARNUNG: Branch umbenennen fehlgeschlagen
)

echo.
echo ===============================================
echo  Setup erfolgreich abgeschlossen!
echo ===============================================
echo.
echo NÄCHSTE SCHRITTE:
echo.
echo 1. Stellen Sie sicher, dass das GitHub Repository existiert:
echo    https://github.com/rschnappi/ha-oekofen
echo.
echo 2. Führen Sie diesen Befehl aus um zu pushen:
echo    git push -u origin main
echo.
echo 3. Geben Sie Ihre GitHub Credentials ein wenn gefragt
echo.
echo ODER falls Sie SSH verwenden:
echo    git remote set-url origin git@github.com:rschnappi/ha-oekofen.git
echo    git push -u origin main
echo.
pause