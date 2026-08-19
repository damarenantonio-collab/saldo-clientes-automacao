@echo off
REM Duplo clique neste arquivo sempre que quiser disparar os e-mails de
REM saldo com os dados mais recentes.
REM
REM Tambem e usado pelo Agendador de Tarefas do Windows para rodar sozinho
REM todo dia (veja o README, secao "Agendando a execucao automatica") -- ao
REM agendar, chame com o argumento "silencioso" para nao ficar esperando
REM alguem apertar uma tecla:
REM     atualizar.bat silencioso

set "MODO=%~1"
cd /d "%~dp0"

if not exist "config\settings.yaml" (
    echo ERRO: config\settings.yaml nao encontrado.
    echo Copie config\settings.example.yaml para config\settings.yaml e ajuste os valores.
    if /i not "%MODO%"=="silencioso" pause
    exit /b 1
)

python main.py
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
    echo Concluido. Veja logs\execucao.log para o historico completo.
) else (
    echo ERRO na execucao (codigo %EXITCODE%^). Veja logs\execucao.log para detalhes.
)

if /i not "%MODO%"=="silencioso" pause
exit /b %EXITCODE%
