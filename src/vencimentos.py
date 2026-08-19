"""Leitura e validação dos vencimentos de renda fixa do mês, a partir da
planilha exportada do BTG (aba "Vencimentos RF").

Assim como em src/saldos.py, o BTG não exporta o banker responsável —
`banker_padrao` é atribuído a toda linha enquanto houver um único banker.
"""

import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

SHEET_PADRAO = "Vencimentos RF"

ALIASES_COLUNA = {
    "conta btg": "conta",
    "codigo do cliente": "cliente",
    "emissor": "emissor",
    "produto": "produto",
    "indexador": "indexador",
    "vencimento": "vencimento",
    "valor liquido - curva cliente": "valor_liquido",
}

COLUNAS_INTERNAS = ["conta", "cliente", "produto", "emissor", "indexador", "vencimento", "valor_liquido"]
COLUNAS_TEXTO = ["conta", "cliente", "produto", "emissor", "indexador"]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().lower()


def load_vencimentos(
    planilha_xlsx: Path,
    banker_padrao: str,
    mes_ref: date,
    sheet_name: str = SHEET_PADRAO,
) -> pd.DataFrame:
    """Lê a aba de vencimentos de renda fixa e retorna só as linhas cujo
    vencimento cai no mês/ano de `mes_ref` (o dia de `mes_ref` é ignorado).

    Colunas do resultado: `banker_id`, `conta`, `cliente`, `produto`,
    `emissor`, `indexador`, `vencimento`, `valor_liquido`.
    """
    bruto = pd.read_excel(planilha_xlsx, sheet_name=sheet_name)

    renomear = {}
    for coluna in bruto.columns:
        chave = ALIASES_COLUNA.get(_normalizar(str(coluna)))
        if chave:
            renomear[coluna] = chave

    df = bruto.rename(columns=renomear)

    faltando = set(COLUNAS_INTERNAS) - set(df.columns)
    if faltando:
        raise RuntimeError(
            f"{planilha_xlsx} (aba '{sheet_name}') está com coluna(s) não reconhecida(s): "
            f"faltam {sorted(faltando)}. Colunas encontradas: {list(bruto.columns)}"
        )

    df = df[COLUNAS_INTERNAS].copy()
    for coluna in COLUNAS_TEXTO:
        df[coluna] = df[coluna].astype(str).str.strip()
    df["vencimento"] = pd.to_datetime(df["vencimento"], errors="coerce")
    df["valor_liquido"] = pd.to_numeric(df["valor_liquido"], errors="coerce")

    df = df[df["vencimento"].notna()]

    do_mes = (df["vencimento"].dt.month == mes_ref.month) & (df["vencimento"].dt.year == mes_ref.year)
    df = df[do_mes].sort_values("vencimento").reset_index(drop=True)

    df["banker_id"] = banker_padrao
    return df
