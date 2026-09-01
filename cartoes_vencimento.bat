@echo off
REM Duplo clique pra rodar o aviso de vencimento de fatura de cartao de
REM credito.
REM
REM Pensado pra ser agendado DIARIAMENTE no Agendador de Tarefas do
REM Windows -- so manda e-mail quando ha algum vencimento dentro da
REM janela de aviso (cartoes_dias_aviso em settings.yaml); nos outros
REM dias nao envia nada. Veja o README, secao do boletim de cartoes.
REM
REM Ao agendar, chame com o argumento "silencioso":
REM     cartoes_vencimento.bat silencioso
REM
REM Em modo silencioso, tudo que aparecer na tela vai tambem pra
REM logs\tarefa_agendada_cartoes.log -- sem isso, um erro nessa etapa
REM (antes do Python conseguir configurar o logger) fica invisivel.

set "MODO=%~1"
cd /d "%~dp0"

if not exist "config\settings.yaml" (
    if /i "%MODO%"=="silencioso" (
        mkdir logs 2>nul
        >>logs\tarefa_agendada_cartoes.log echo %date% %time% ERRO: config\settings.yaml nao encontrado.
    ) else (
        echo ERRO: config\settings.yaml nao encontrado.
        echo Copie config\settings.example.yaml para config\settings.yaml e ajuste os valores.
        pause
    )
    exit /b 1
)

if /i "%MODO%"=="silencioso" (
    mkdir logs 2>nul
    >>logs\tarefa_agendada_cartoes.log echo ---- %date% %time% ----
    python cartoes_vencimento.py >>logs\tarefa_agendada_cartoes.log 2>&1
) else (
    python cartoes_vencimento.py
)
set "EXITCODE=%ERRORLEVEL%"

if /i "%MODO%"=="silencioso" (
    >>logs\tarefa_agendada_cartoes.log echo codigo de saida: %EXITCODE%
) else (
    echo.
    if "%EXITCODE%"=="0" (
        echo Concluido. Veja logs\execucao_cartoes.log para o historico completo.
    ) else (
        echo ERRO na execucao ^(codigo %EXITCODE%^). Veja logs\execucao_cartoes.log para detalhes.
    )
    pause
)

exit /b %EXITCODE%
