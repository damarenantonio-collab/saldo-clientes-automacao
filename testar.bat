@echo off
REM Duplo clique para rodar em modo DRY-RUN: nenhum e-mail e enviado.
REM O HTML de cada banker e gravado em saida_teste\<banker_id>.html para
REM voce conferir o conteudo antes de ativar o envio de verdade.

cd /d "%~dp0"

if not exist "config\settings.yaml" (
    echo ERRO: config\settings.yaml nao encontrado.
    echo Copie config\settings.example.yaml para config\settings.yaml e ajuste os valores.
    pause
    exit /b 1
)

python main.py --dry-run
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
    echo Concluido. Confira os arquivos .html em saida_teste\
) else (
    echo ERRO na execucao (codigo %EXITCODE%^). Veja logs\execucao.log para detalhes.
)

pause
exit /b %EXITCODE%
