@echo off
REM Duplo clique para rodar o boletim de vencimentos em modo DRY-RUN:
REM nenhum e-mail e enviado. O HTML de cada banker e gravado em
REM saida_teste\vencimentos-<banker_id>.html para voce conferir.
REM
REM Roda pro mes atual, ignorando a checagem de "primeiro dia util" (o
REM dry-run sempre gera o preview, nao importa o dia).
REM
REM Pra simular outro mes (ex: um que tenha vencimento de verdade nos
REM dados de exemplo), rode direto:
REM     python vencimentos_mensal.py --dry-run --mes 10 --ano 2026

cd /d "%~dp0"

if not exist "config\settings.yaml" (
    echo ERRO: config\settings.yaml nao encontrado.
    echo Copie config\settings.example.yaml para config\settings.yaml e ajuste os valores.
    pause
    exit /b 1
)

python vencimentos_mensal.py --dry-run
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
    echo Concluido. Confira os arquivos .html em saida_teste\
) else (
    echo ERRO na execucao ^(codigo %EXITCODE%^). Veja logs\execucao_vencimentos.log para detalhes.
)

pause
exit /b %EXITCODE%
