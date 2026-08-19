"""Guarda um snapshot diário agregado dos envios (auditoria), sem dado de
cliente — só contagem e saldo total por banker.
"""

from datetime import date
from pathlib import Path

import pandas as pd

from .agrupador import GrupoBanker


def append_snapshot(grupos: list[GrupoBanker], data_referencia: date, history_path: Path) -> None:
    linhas = [
        {
            "data": data_referencia.isoformat(),
            "banker_id": g.banker_id,
            "banker_nome": g.banker_nome,
            "qtd_clientes": len(g.clientes),
            "saldo_total": round(float(g.clientes["saldo"].sum()), 2),
        }
        for g in grupos
    ]
    novo = pd.DataFrame(linhas)

    history_path.parent.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        existente = pd.read_csv(history_path)
        combinado = pd.concat([existente, novo], ignore_index=True)
    else:
        combinado = novo

    combinado.to_csv(history_path, index=False)
