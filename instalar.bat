@echo off
REM Duplo clique neste arquivo para instalar tudo que o projeto precisa.
REM So precisa rodar uma vez (ou de novo se der algum erro estranho).
REM
REM Nao usa ambiente virtual (.venv) de proposito -- em algumas maquinas
REM (antivirus corporativo/EDR, OneDrive sincronizando a pasta) a criacao
REM do .venv falha de forma intermitente, mesmo com o Python correto
REM instalado. Instalar direto no Python do usuario com --user e mais
REM simples e, na pratica, mais confiavel nessas maquinas.

cd /d "%~dp0"

echo Instalando dependencias...
python -m pip install --user -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERRO ao instalar as dependencias.
    echo.
    echo Se a mensagem acima disser que "python" nao e reconhecido, ou se
    echo abriu a Microsoft Store: instale o Python de verdade em
    echo https://www.python.org/downloads/windows/ (marque "Add python.exe
    echo to PATH" no instalador), feche esta janela, abra uma nova, e de
    echo duplo clique aqui de novo.
    pause
    exit /b 1
)

echo.
echo ==========================================================
echo Instalacao concluida!
echo.
echo Proximos passos: edite os arquivos dentro da pasta "config":
echo   1. copie config\bankers.example.csv para config\bankers.csv
echo      e preencha com o(s) banker(s) reais (banker_id, nome, e-mail)
echo   2. copie config\settings.example.yaml para config\settings.yaml
echo      e ajuste saldos_xlsx (caminho do Excel baixado do BTG),
echo      banker_padrao e os dados de SMTP (comece com
echo      modo_teste.ativo: true)
echo.
echo Depois disso, de duplo clique em atualizar.bat
echo ==========================================================
pause
