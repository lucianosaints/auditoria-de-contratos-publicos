@echo off
setlocal
chcp 65001 >nul
title Auditoria Cidada - Painel
pushd "%~dp0frontend"
if errorlevel 1 exit /b 1
echo ========================================
echo       Auditoria Cidada - Painel Web
echo ========================================
echo.
where node >nul 2>&1
if errorlevel 1 goto sem_node
where npm.cmd >nul 2>&1
if errorlevel 1 goto sem_node
if exist "node_modules\vite\bin\vite.js" goto pronto
echo Instalando dependencias do painel. Aguarde...
call npm.cmd install --no-audit --no-fund
if errorlevel 1 goto erro
:pronto
if /i "%~1"=="--verificar" goto verificar
echo O painel abrira em http://127.0.0.1:5173
echo Mantenha esta janela aberta para usar o painel.
echo Use Ctrl+C para encerrar.
echo.
start "" /b powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:5173'"
call npm.cmd run dev
goto resultado
:verificar
call npm.cmd run build
goto resultado
:sem_node
echo ERRO: Node.js e npm nao foram encontrados.
echo Instale Node.js LTS e abra novamente este arquivo.
goto erro
:resultado
set "PAINEL_STATUS=%ERRORLEVEL%"
goto finalizar
:erro
set "PAINEL_STATUS=1"
echo Nao foi possivel iniciar. Confira as mensagens acima.
:finalizar
if /i not "%~1"=="--verificar" pause
popd
exit /b %PAINEL_STATUS%
