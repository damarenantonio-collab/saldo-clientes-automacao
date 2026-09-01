"""Leitura do mapeamento banker_id -> nome/e-mail, e a função que
deriva um banker_id a partir do nome do responsável nas planilhas
(saldo e vencimentos usam a mesma lógica).
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"banker_id", "banker_nome", "email"}


def slugify_banker(nome: str) -> str:
    """Transforma "Eduardo Rego" em "eduardo_rego" — usado como
    `banker_id` (precisa bater com o `banker_id` cadastrado em
    bankers.csv)."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    sem_acento = sem_acento.strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento).strip("_")


def load_bankers(bankers_csv: Path) -> dict:
    """Lê o CSV de bankers e retorna {banker_id: {"nome": ..., "email": ...}}."""
    df = pd.read_csv(bankers_csv, dtype=str).fillna("")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise RuntimeError(f"{bankers_csv} está faltando coluna(s): {sorted(missing)}")

    duplicados = df["banker_id"][df["banker_id"].duplicated()].unique()
    if len(duplicados) > 0:
        raise RuntimeError(
            f"{bankers_csv} tem banker_id duplicado: {list(duplicados)}. "
            f"Cada banker_id deve aparecer uma única vez."
        )

    bankers = {}
    for _, row in df.iterrows():
        banker_id = row["banker_id"].strip()
        bankers[banker_id] = {"nome": row["banker_nome"].strip(), "email": row["email"].strip()}
    return bankers
