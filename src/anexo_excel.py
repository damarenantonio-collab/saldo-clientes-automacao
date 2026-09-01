"""Gera o anexo .xlsx com os dados de um banker (saldo ou vencimentos),
pra acompanhar a tabela em imagem no corpo do e-mail — mais fácil de
abrir numa planilha própria do que copiar da imagem.
"""

from io import BytesIO

import pandas as pd


def gerar_xlsx(df: pd.DataFrame, colunas: dict[str, str]) -> bytes:
    """`colunas` mapeia nome interno da coluna -> cabeçalho de exibição,
    na ordem em que devem aparecer na planilha."""
    saida = df[list(colunas.keys())].rename(columns=colunas)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        saida.to_excel(writer, index=False, sheet_name="Dados")
    return buffer.getvalue()
