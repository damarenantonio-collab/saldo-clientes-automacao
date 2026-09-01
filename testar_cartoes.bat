@echo off
REM Duplo clique para rodar o aviso de cartao de credito em modo
REM DRY-RUN: nenhum e-mail e enviado. O HTML e gravado em
REM saida_teste\cartoes-<banker_id>.html para voce conferir.
REM
REM Roda pra data de hoje. Se nao houver nenhum vencimento dentro da
REM janela de aviso, nenhum arquivo e gerado (mesmo comportamento do
REM envio real).
REM
REM Pra simular outra data (ex: perto do vencimento de algum cliente
REM de teste), rode direto:
REM     python cartoes_vencimento.py --dry-run --data 2026-09-14

cd /d "%~dp0"

if not exist "config\settings.yaml" (
    echo ERRO: config\settings.yaml nao encontrado.
    echo Copie config\settings.example.yaml para config\settings.yaml e ajuste os valores.
    pause
    exit /b 1
)

python cartoes_vencimento.py --dry-run
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
    echo Concluido. Confira os arquivos .html em saida_teste\ ^(se nao aparecer nenhum, e porque nao ha vencimento na janela de aviso^).
) else (
    echo ERRO na execucao ^(codigo %EXITCODE%^). Veja logs\execucao_cartoes.log para detalhes.
)

pause
exit /b %EXITCODE%
