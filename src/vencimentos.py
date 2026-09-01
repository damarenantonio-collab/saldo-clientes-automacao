"""Leitura e validação dos vencimentos de renda fixa, a partir da
planilha consolidada do escritório inteiro (`Vencimentos_RF.xlsx`,
aba "Export").

Essa planilha já traz o banker responsável por cada linha (coluna
"Responsável") — o banker_id de cada linha vem direto do arquivo
(veja `src/bankers.slugify_banker`), suportando quantos responsáveis
existirem sem configuração extra. Mesmo princípio de src/saldos.py.
"""

import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

from .bankers import slugify_banker

SHEET_PADRAO = "Export"

ALIASES_COLUNA = {
    "conta btg": "conta",
    "nome do cliente": "cliente",
    "descricao": "produto",
    "valor liquido": "valor_liquido",
    "data vencimento": "vencimento",
    "responsavel": "responsavel",
}

COLUNAS_ORIGEM = ["conta", "cliente", "produto", "valor_liquido", "vencimento", "responsavel"]
COLUNAS_TEXTO = ["conta", "cliente", "produto", "responsavel"]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().lower()


def _carregar_bruto(planilha_xlsx: Path, sheet_name: str) -> pd.DataFrame:
    bruto = pd.read_excel(planilha_xlsx, sheet_name=sheet_name)

    renomear = {}
    for coluna in bruto.columns:
        chave = ALIASES_COLUNA.get(_normalizar(str(coluna)))
        if chave:
            renomear[coluna] = chave

    df = bruto.rename(columns=renomear)

    faltando = set(COLUNAS_ORIGEM) - set(df.columns)
    if faltando:
        raise RuntimeError(
            f"{planilha_xlsx} (aba '{sheet_name}') está com coluna(s) não reconhecida(s): "
            f"faltam {sorted(faltando)}. Colunas encontradas: {list(bruto.columns)}"
        )

    df = df[COLUNAS_ORIGEM].copy()
    for coluna in COLUNAS_TEXTO:
        df[coluna] = df[coluna].astype(str).str.strip()
    df["vencimento"] = pd.to_datetime(df["vencimento"], errors="coerce")
    df["valor_liquido"] = pd.to_numeric(df["valor_liquido"], errors="coerce")
    df = df[df["vencimento"].notna()]

    return df


def bankers_conhecidos(planilha_xlsx: Path, sheet_name: str = SHEET_PADRAO) -> set[str]:
    """`banker_id`s de todo responsável que aparece na planilha, em
    qualquer mês — usado pra saber pra quem mandar um e-mail de "não há
    vencimento este mês" mesmo quando ninguém desse responsável vence
    no mês específico sendo processado."""
    df = _carregar_bruto(planilha_xlsx, sheet_name)
    return set(df["responsavel"].map(slugify_banker))


def load_vencimentos(planilha_xlsx: Path, mes_ref: date, sheet_name: str = SHEET_PADRAO) -> pd.DataFrame:
    """Lê a planilha de vencimentos e retorna só as linhas cujo
    vencimento cai no mês/ano de `mes_ref` (o dia de `mes_ref` é ignorado).

    Colunas do resultado: `banker_id`, `conta`, `cliente`, `produto`,
    `vencimento`, `valor_liquido`.
    """
    df = _carregar_bruto(planilha_xlsx, sheet_name)

    do_mes = (df["vencimento"].dt.month == mes_ref.month) & (df["vencimento"].dt.year == mes_ref.year)
    df = df[do_mes].copy()

    df["banker_id"] = df["responsavel"].map(slugify_banker)
    df = df.drop(columns=["responsavel"]).sort_values(["banker_id", "vencimento"]).reset_index(drop=True)
    return df
