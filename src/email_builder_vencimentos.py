"""Monta o corpo HTML do e-mail mensal de vencimentos de renda fixa
para um único banker. Mesmo estilo visual do boletim de saldo (veja
src/email_builder.py) — só muda o texto e a tabela.
"""

from datetime import date

from .agrupador import GrupoBanker
from .email_base import montar_corpo_html as _montar_corpo_html
from .email_base import primeiro_nome
from .meses import nome_mes

LARGURA_IMAGEM = 760


def montar_corpo_html(
    grupo: GrupoBanker,
    assinatura: str,
    mes_ref: date,
    imagem_src: str | None,
    aviso_teste: str | None = None,
) -> str:
    """`imagem_src` é `cid:<id>` no envio real, uma data URI no dry-run,
    ou `None` quando não há vencimento nenhum no mês (nesse caso a
    tabela não aparece, só o aviso em texto).
    """
    mes_ano = f"{nome_mes(mes_ref.month)} de {mes_ref.year}"
    saudacao = f"Bom dia {primeiro_nome(grupo.banker_nome)}, tudo bem?"

    if imagem_src:
        paragrafos = [
            saudacao,
            f"Segue abaixo os vencimentos de renda fixa de {mes_ano} dos seus clientes no BTG.",
        ]
    else:
        paragrafos = [
            saudacao,
            f"Não há vencimentos de renda fixa previstos para {mes_ano} entre os seus clientes no BTG.",
        ]

    return _montar_corpo_html(
        paragrafos, assinatura, imagem_src=imagem_src, imagem_largura=LARGURA_IMAGEM, aviso_teste=aviso_teste
    )
