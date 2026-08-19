"""Agrupa o saldo dos clientes por banker responsável.

Este é o ponto central do controle de acesso da automação: cada grupo
retornado por `agrupar_por_banker` contém *apenas* as linhas daquele
banker, e é isso que vira o corpo do e-mail dele. Nenhum outro módulo
tem acesso ao DataFrame completo depois daqui — cada banker só recebe o
subconjunto que já veio filtrado por este módulo.
"""

import logging
from dataclasses import dataclass

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class GrupoBanker:
    banker_id: str
    banker_nome: str
    email: str
    clientes: pd.DataFrame  # apenas as linhas deste banker


def agrupar_por_banker(saldos: pd.DataFrame, bankers: dict) -> tuple[list[GrupoBanker], list[str]]:
    """Retorna (grupos prontos para envio, banker_ids sem e-mail cadastrado).

    Um banker_id presente em `saldos` mas ausente (ou sem e-mail) em
    `bankers` NÃO gera grupo — os clientes dele ficam de fora do envio
    dessa execução (nunca são despachados pra um destinatário errado) e o
    banker_id entra na lista de pendências, pra ser alertado.
    """
    grupos = []
    pendentes = []

    for banker_id, clientes in saldos.groupby("banker_id", sort=True):
        info = bankers.get(banker_id)
        if not info or not info.get("email"):
            pendentes.append(banker_id)
            logger.warning(
                "banker_id '%s' tem %d cliente(s) em saldos.csv mas não tem e-mail "
                "cadastrado em bankers.csv — não enviado nesta execução.",
                banker_id,
                len(clientes),
            )
            continue

        grupos.append(
            GrupoBanker(
                banker_id=banker_id,
                banker_nome=info["nome"] or banker_id,
                email=info["email"],
                clientes=clientes.reset_index(drop=True),
            )
        )

    _validar_sem_vazamento(saldos, grupos, pendentes)
    return grupos, pendentes


def _validar_sem_vazamento(saldos: pd.DataFrame, grupos: list[GrupoBanker], pendentes: list[str]) -> None:
    """Confere que todo cliente do arquivo original está em exatamente um
    grupo (ou na lista de pendentes) — nunca em zero nem em mais de um.
    Falha alto e cedo em vez de arriscar um envio incorreto.
    """
    contas_originais = set(zip(saldos["banker_id"], saldos["conta"]))

    contas_agrupadas = []
    for grupo in grupos:
        contas_agrupadas.extend(zip(grupo.clientes["banker_id"], grupo.clientes["conta"]))

    if len(contas_agrupadas) != len(set(contas_agrupadas)):
        raise RuntimeError("Inconsistência interna: conta de cliente apareceu em mais de um grupo de banker.")

    contas_pendentes = {(b, c) for b, c in contas_originais if b in pendentes}
    esperado = set(contas_agrupadas) | contas_pendentes

    if esperado != contas_originais:
        raise RuntimeError(
            "Inconsistência interna: nem toda linha de saldos.csv foi contabilizada "
            "em um grupo de banker ou na lista de pendências. Envio abortado por segurança."
        )
