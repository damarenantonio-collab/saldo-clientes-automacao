"""Leitura e validação do saldo em conta dos clientes, a partir da
planilha exportada do BTG (aba "Saldo Diário").

O BTG identifica cada cliente por um código (ex: "AOAK_MA"), não por
nome, e não exporta o banker responsável — essa informação não existe
nesse arquivo. Por isso, hoje, `banker_padrao` (de settings.yaml) é
atribuído a todo mundo. Quando existir mais de um banker, troque isso
por uma consulta a um mapeamento código -> banker_id (veja o README,
seção "Múltiplos bankers").
"""

import unicodedata
from pathlib import Path

import pandas as pd

SHEET_PADRAO = "Saldo Diário"

# aceita pequenas variações de nome de coluna entre exportações do BTG
# (a própria planilha já varia entre abas: "Conta BTG" vs "Conta do BTG")
ALIASES_COLUNA = {
    "conta btg": "conta",
    "conta do btg": "conta",
    "codigo do cliente": "cliente",
    "saldo": "saldo",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().lower()


def load_saldos(saldos_xlsx: Path, banker_padrao: str, sheet_name: str = SHEET_PADRAO) -> pd.DataFrame:
    """Lê a aba de saldo em conta do Excel do BTG e retorna um DataFrame
    com as colunas internas `banker_id`, `cliente`, `conta`, `saldo`.

    Uma linha por conta BTG (um mesmo código de cliente pode ter mais de
    uma conta). `banker_id` vem de `banker_padrao` — todo cliente do
    arquivo é tratado como sendo desse banker.
    """
    bruto = pd.read_excel(saldos_xlsx, sheet_name=sheet_name, dtype=str)

    renomear = {}
    for coluna in bruto.columns:
        chave = ALIASES_COLUNA.get(_normalizar(str(coluna)))
        if chave:
            renomear[coluna] = chave

    df = bruto.rename(columns=renomear)

    faltando = {"conta", "cliente", "saldo"} - set(df.columns)
    if faltando:
        raise RuntimeError(
            f"{saldos_xlsx} (aba '{sheet_name}') está com coluna(s) não reconhecida(s): "
            f"faltam {sorted(faltando)}. Colunas encontradas: {list(bruto.columns)}"
        )

    df = df[["conta", "cliente", "saldo"]].copy()
    df["cliente"] = df["cliente"].str.strip()
    df["conta"] = df["conta"].str.strip()
    df["saldo"] = pd.to_numeric(df["saldo"], errors="coerce")
    df["banker_id"] = banker_padrao

    sem_cliente = df["cliente"].isna() | (df["cliente"] == "")
    if sem_cliente.any():
        raise RuntimeError(f"{sem_cliente.sum()} linha(s) sem código de cliente preenchido.")

    saldo_invalido = df["saldo"].isna()
    if saldo_invalido.any():
        raise RuntimeError(f"{saldo_invalido.sum()} linha(s) com saldo inválido (não numérico).")

    return df
