"""Monta o corpo HTML do e-mail mensal de vencimentos de renda fixa
para um único banker.
"""

from datetime import date

from .agrupador import GrupoBanker
from .email_base import montar_bloco
from .email_base import montar_corpo_html as _montar_corpo_html
from .email_base import primeiro_nome
from .meses import nome_mes

LARGURA_IMAGEM = 640


def texto_vencimentos(banker_nome: str, mes_ref: date, tem_vencimento: bool) -> list[str]:
    mes_ano = f"{nome_mes(mes_ref.month)} de {mes_ref.year}"
    saudacao = f"Bom dia {primeiro_nome(banker_nome)}, tudo bem?"
    if tem_vencimento:
        return [saudacao, f"Segue abaixo os vencimentos de renda fixa de {mes_ano} dos seus clientes no BTG."]
    return [saudacao, f"Não há vencimentos de renda fixa previstos para {mes_ano} entre os seus clientes no BTG."]


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
    bloco = montar_bloco(
        texto_vencimentos(grupo.banker_nome, mes_ref, tem_vencimento=bool(imagem_src)),
        imagem_src=imagem_src,
        imagem_largura=LARGURA_IMAGEM,
    )
    return _montar_corpo_html([bloco], assinatura, aviso_teste=aviso_teste)
