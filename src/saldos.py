"""Leitura e validação do arquivo de saldo em conta dos clientes."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"banker_id", "cliente", "conta", "saldo"}


def load_saldos(saldos_csv: Path) -> pd.DataFrame:
    """Lê o CSV de saldos e valida as colunas obrigatórias.

    Uma linha por cliente. `banker_id` identifica o banker responsável por
    aquele cliente e é a chave usada depois para decidir pra quem cada
    linha pode ser enviada — nunca inclua nessa planilha um cliente sem
    `banker_id` correto, ou ele não aparecerá em nenhum e-mail.
    """
    df = pd.read_csv(saldos_csv, dtype={"banker_id": str, "cliente": str, "conta": str})

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise RuntimeError(f"{saldos_csv} está faltando coluna(s): {sorted(missing)}")

    df["banker_id"] = df["banker_id"].str.strip()
    df["saldo"] = pd.to_numeric(df["saldo"], errors="coerce")

    sem_banker = df["banker_id"].isna() | (df["banker_id"] == "")
    if sem_banker.any():
        raise RuntimeError(
            f"{sem_banker.sum()} linha(s) de {saldos_csv} sem banker_id preenchido. "
            f"Corrija o arquivo antes de enviar — uma linha sem banker_id não tem "
            f"como ser roteada com segurança para o e-mail certo."
        )

    saldo_invalido = df["saldo"].isna()
    if saldo_invalido.any():
        raise RuntimeError(
            f"{saldo_invalido.sum()} linha(s) de {saldos_csv} com saldo inválido (não numérico)."
        )

    return df
