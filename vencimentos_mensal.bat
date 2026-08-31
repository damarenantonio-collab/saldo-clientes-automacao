@echo off
REM Duplo clique pra rodar o boletim de vencimentos de renda fixa.
REM
REM Pensado pra ser agendado TODO DIA UTIL (nao so uma vez por mes) --
REM o proprio vencimentos_mensal.py decide se hoje e o primeiro dia util
REM do mes; nos outros dias ele sai sem enviar nada e sem erro. Veja o
REM README, secao "Agendando (vencimentos)".
REM
REM Ao agendar, chame com o argumento "silencioso":
REM     vencimentos_mensal.bat silencioso
REM
REM Em modo silencioso, tudo que aparecer na tela vai tambem pra
REM logs\tarefa_agendada_vencimentos.log -- sem isso, um erro nessa
REM etapa (antes do Python conseguir configurar o logger) fica invisivel.

set "MODO=%~1"
cd /d "%~dp0"

if not exist "config\settings.yaml" (
    if /i "%MODO%"=="silencioso" (
        mkdir logs 2>nul
        >>logs\tarefa_agendada_vencimentos.log echo %date% %time% ERRO: config\settings.yaml nao encontrado.
    ) else (
        echo ERRO: config\settings.yaml nao encontrado.
        echo Copie config\settings.example.yaml para config\settings.yaml e ajuste os valores.
        pause
    )
    exit /b 1
)

if /i "%MODO%"=="silencioso" (
    mkdir logs 2>nul
    >>logs\tarefa_agendada_vencimentos.log echo ---- %date% %time% ----
    python vencimentos_mensal.py >>logs\tarefa_agendada_vencimentos.log 2>&1
) else (
    python vencimentos_mensal.py
)
set "EXITCODE=%ERRORLEVEL%"

if /i "%MODO%"=="silencioso" (
    >>logs\tarefa_agendada_vencimentos.log echo codigo de saida: %EXITCODE%
) else (
    echo.
    if "%EXITCODE%"=="0" (
        echo Concluido. Veja logs\execucao_vencimentos.log para o historico completo.
    ) else (
        echo ERRO na execucao ^(codigo %EXITCODE%^). Veja logs\execucao_vencimentos.log para detalhes.
    )
    pause
)

exit /b %EXITCODE%
