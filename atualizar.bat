@echo off
REM Duplo clique neste arquivo sempre que quiser disparar os e-mails de
REM saldo com os dados mais recentes.
REM
REM Tambem e usado pelo Agendador de Tarefas do Windows para rodar sozinho
REM todo dia (veja o README, secao "Agendando a execucao automatica") -- ao
REM agendar, chame com o argumento "silencioso" para nao ficar esperando
REM alguem apertar uma tecla:
REM     atualizar.bat silencioso
REM
REM Em modo silencioso, tudo que aparecer na tela (incluindo erros do
REM proprio Windows, tipo "python nao reconhecido") vai tambem pra
REM logs\tarefa_agendada.log -- o Agendador de Tarefas nao mostra a tela
REM nem guarda o que foi impresso, entao sem isso um erro nessa etapa
REM fica invisivel.

set "MODO=%~1"
cd /d "%~dp0"

if not exist "config\settings.yaml" (
    if /i "%MODO%"=="silencioso" (
        mkdir logs 2>nul
        >>logs\tarefa_agendada.log echo %date% %time% ERRO: config\settings.yaml nao encontrado.
    ) else (
        echo ERRO: config\settings.yaml nao encontrado.
        echo Copie config\settings.example.yaml para config\settings.yaml e ajuste os valores.
        pause
    )
    exit /b 1
)

if /i "%MODO%"=="silencioso" (
    mkdir logs 2>nul
    >>logs\tarefa_agendada.log echo ---- %date% %time% ----
    python main.py >>logs\tarefa_agendada.log 2>&1
) else (
    python main.py
)
set "EXITCODE=%ERRORLEVEL%"

if /i "%MODO%"=="silencioso" (
    >>logs\tarefa_agendada.log echo codigo de saida: %EXITCODE%
) else (
    echo.
    if "%EXITCODE%"=="0" (
        echo Concluido. Veja logs\execucao.log para o historico completo.
    ) else (
        echo ERRO na execucao ^(codigo %EXITCODE%^). Veja logs\execucao.log para detalhes.
    )
    pause
)

exit /b %EXITCODE%
