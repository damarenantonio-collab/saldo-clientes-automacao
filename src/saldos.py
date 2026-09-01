"""Leitura e validação do saldo em conta dos clientes, a partir da
planilha consolidada do escritório inteiro (`Saldo_em_CC_BTG.xlsx`,
aba "Export").

Essa planilha já traz o banker responsável por cada linha (coluna
"Responsável") — o banker_id de cada linha vem direto do arquivo
(veja `src/bankers.slugify_banker`), suportando quantos responsáveis
existirem sem configuração extra. Mesmo princípio de src/vencimentos.py.
"""

import unicodedata
from pathlib import Path

import pandas as pd

from .bankers import slugify_banker

SHEET_PADRAO = "Export"

# aceita pequenas variações de nome de coluna entre exportações do BTG
ALIASES_COLUNA = {
    "conta btg": "conta",
    "conta do btg": "conta",
    "nome do cliente": "cliente",
    "codigo do cliente": "cliente",
    "saldo": "saldo",
    "responsavel": "responsavel",
}

COLUNAS_ORIGEM = ["conta", "cliente", "saldo", "responsavel"]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().lower()


def load_saldos(saldos_xlsx: Path, sheet_name: str = SHEET_PADRAO) -> pd.DataFrame:
    """Lê a planilha de saldo em conta e retorna um DataFrame com as
    colunas internas `banker_id`, `cliente`, `conta`, `saldo`.

    Uma linha por conta (um mesmo cliente pode ter mais de uma conta).
    """
    bruto = pd.read_excel(saldos_xlsx, sheet_name=sheet_name, dtype=str)

    renomear = {}
    for coluna in bruto.columns:
        chave = ALIASES_COLUNA.get(_normalizar(str(coluna)))
        if chave:
            renomear[coluna] = chave

    df = bruto.rename(columns=renomear)

    faltando = set(COLUNAS_ORIGEM) - set(df.columns)
    if faltando:
        raise RuntimeError(
            f"{saldos_xlsx} (aba '{sheet_name}') está com coluna(s) não reconhecida(s): "
            f"faltam {sorted(faltando)}. Colunas encontradas: {list(bruto.columns)}"
        )

    df = df[COLUNAS_ORIGEM].copy()
    df["cliente"] = df["cliente"].str.strip()
    df["conta"] = df["conta"].str.strip()
    df["responsavel"] = df["responsavel"].str.strip()
    df["saldo"] = pd.to_numeric(df["saldo"], errors="coerce")

    sem_cliente = df["cliente"].isna() | (df["cliente"] == "")
    if sem_cliente.any():
        raise RuntimeError(f"{sem_cliente.sum()} linha(s) sem código de cliente preenchido.")

    saldo_invalido = df["saldo"].isna()
    if saldo_invalido.any():
        raise RuntimeError(f"{saldo_invalido.sum()} linha(s) com saldo inválido (não numérico).")

    df["banker_id"] = df["responsavel"].map(slugify_banker)
    return df.drop(columns=["responsavel"])
