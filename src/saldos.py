"""Leitura e validação do saldo em conta dos clientes, a partir da
planilha consolidada do escritório inteiro (`Saldo_em_CC_BTG.xlsx`).

Essa planilha tem duas abas com o mesmo formato — "Investimentos" e
"Banking" — cada uma virando uma tabela separada no e-mail (veja
main.py). Cada linha já traz o banker responsável (coluna
"Responsável") — o banker_id de cada linha vem direto do arquivo
(veja `src/bankers.slugify_banker`), suportando quantos responsáveis
existirem sem configuração extra. Mesmo princípio de src/vencimentos.py.
"""

import unicodedata
from pathlib import Path

import pandas as pd

from .bankers import slugify_banker

SHEET_INVESTIMENTOS_PADRAO = "Investimentos"
SHEET_BANKING_PADRAO = "Banking"

COLUNAS_ORIGEM = ["conta", "cliente", "saldo", "responsavel"]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().lower()


def _mapear_coluna(nome_coluna: str) -> str | None:
    """Aceita pequenas variações de nome de coluna entre exportações do
    BTG — inclusive a coluna de saldo tendo um nome diferente por aba
    (ex: "Saldo" em Investimentos, "Saldo Banking (R$)" em Banking)."""
    chave = _normalizar(nome_coluna)
    if chave in ("conta btg", "conta do btg"):
        return "conta"
    if chave in ("nome do cliente", "codigo do cliente"):
        return "cliente"
    if chave.startswith("saldo"):
        return "saldo"
    if chave == "responsavel":
        return "responsavel"
    return None


def load_saldos(saldos_xlsx: Path, sheet_name: str) -> pd.DataFrame:
    """Lê uma aba da planilha de saldo em conta e retorna um DataFrame
    com as colunas internas `banker_id`, `cliente`, `conta`, `saldo`.

    Uma linha por conta (um mesmo cliente pode ter mais de uma conta).
    """
    bruto = pd.read_excel(saldos_xlsx, sheet_name=sheet_name, dtype=str)

    renomear = {}
    for coluna in bruto.columns:
        chave = _mapear_coluna(str(coluna))
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
