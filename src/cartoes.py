"""Leitura e validação da planilha de controle de vencimento de fatura
de cartão de crédito, mantida manualmente (não vem do BTG).

Diferente de saldos.py/vencimentos.py, essa planilha não tem uma
coluna de "Responsável" — hoje todos os clientes cadastrados aqui
pertencem a um único banker, configurado em `cartoes_banker_id` no
settings.yaml (veja README, seção do boletim de cartões).
"""

import calendar
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

SHEET_PADRAO = "Clientes"

ATIVO_VALORES_VALIDOS = {"sim", "s", "yes", "true", "1"}

COLUNAS_ORIGEM = ["cliente", "cartao", "dia_vencimento", "ativo"]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    sem_pontuacao = sem_acento.replace(".", "").replace("/", " ")
    return " ".join(sem_pontuacao.strip().lower().split())


def _localizar_linha_cabecalho(bruto: pd.DataFrame) -> int:
    """A planilha tem linhas de instrução antes do cabeçalho de
    verdade — procura a linha cuja primeira célula é "Cliente"."""
    for i in range(min(10, len(bruto))):
        primeira_celula = bruto.iloc[i, 0]
        if isinstance(primeira_celula, str) and _normalizar(primeira_celula) == "cliente":
            return i
    raise RuntimeError(
        "Não encontrei a linha de cabeçalho (coluna 'Cliente') nas primeiras 10 linhas da planilha."
    )


def _proxima_data(dia_vencimento: int, hoje: date) -> date:
    """Próxima ocorrência do dia `dia_vencimento` a partir de `hoje`
    (inclusive). Se o mês não tiver esse dia (ex: 31 em fevereiro),
    usa o último dia do mês."""
    ano, mes = hoje.year, hoje.month
    for _ in range(2):  # tenta o mês atual, depois o próximo
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        candidata = date(ano, mes, min(dia_vencimento, ultimo_dia))
        if candidata >= hoje:
            return candidata
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1
    raise AssertionError("não deveria chegar aqui")  # pragma: no cover


def load_cartoes(cartoes_xlsx: Path, sheet_name: str = SHEET_PADRAO, hoje: date | None = None) -> pd.DataFrame:
    """Lê a planilha de controle de cartões e retorna um DataFrame, uma
    linha por cartão **ativo**, com as colunas `cliente`, `cartao`,
    `dia_vencimento`, `proximo_vencimento` e `dias_ate_vencer` (0 =
    vence hoje, 1 = vence amanhã, etc).
    """
    hoje = hoje or date.today()

    bruto_sem_cabecalho = pd.read_excel(cartoes_xlsx, sheet_name=sheet_name, header=None)
    linha_cabecalho = _localizar_linha_cabecalho(bruto_sem_cabecalho)

    bruto = pd.read_excel(cartoes_xlsx, sheet_name=sheet_name, header=linha_cabecalho, dtype=str)

    renomear = {}
    for coluna in bruto.columns:
        chave = _normalizar(str(coluna))
        if chave == "cliente":
            renomear[coluna] = "cliente"
        elif chave.startswith("cartao"):
            renomear[coluna] = "cartao"
        elif chave.startswith("dia do venc"):
            renomear[coluna] = "dia_vencimento"
        elif chave == "ativo":
            renomear[coluna] = "ativo"

    df = bruto.rename(columns=renomear)

    faltando = set(COLUNAS_ORIGEM) - set(df.columns)
    if faltando:
        raise RuntimeError(
            f"{cartoes_xlsx} (aba '{sheet_name}') está com coluna(s) não reconhecida(s): "
            f"faltam {sorted(faltando)}. Colunas encontradas: {list(bruto.columns)}"
        )

    df = df[COLUNAS_ORIGEM].copy()
    df["cliente"] = df["cliente"].str.strip()
    df["cartao"] = df["cartao"].fillna("").str.strip()
    df = df[df["cliente"].notna() & (df["cliente"] != "")]

    ativo_normalizado = df["ativo"].fillna("").str.strip().str.lower()
    df = df[ativo_normalizado.isin(ATIVO_VALORES_VALIDOS)].drop(columns=["ativo"])

    df["dia_vencimento"] = pd.to_numeric(df["dia_vencimento"], errors="coerce")
    dia_invalido = df["dia_vencimento"].isna() | ~df["dia_vencimento"].between(1, 31)
    if dia_invalido.any():
        raise RuntimeError(
            f"{int(dia_invalido.sum())} linha(s) com 'Dia do Venc.' inválido "
            f"(precisa ser um número de 1 a 31)."
        )
    df["dia_vencimento"] = df["dia_vencimento"].astype(int)

    df["proximo_vencimento"] = df["dia_vencimento"].apply(lambda d: _proxima_data(d, hoje))
    df["dias_ate_vencer"] = df["proximo_vencimento"].apply(lambda dt: (dt - hoje).days)

    return df.reset_index(drop=True)
