"""Monta o corpo HTML do e-mail de aviso de vencimento de fatura de
cartão de crédito para um único banker.
"""

from .agrupador import GrupoBanker
from .email_base import montar_bloco
from .email_base import montar_corpo_html as _montar_corpo_html
from .email_base import primeiro_nome

LARGURA_IMAGEM = 640


def texto_cartoes(banker_nome: str) -> list[str]:
    saudacao = f"Bom dia {primeiro_nome(banker_nome)}, tudo bem?"
    return [saudacao, "Segue abaixo o vencimento da fatura de cartão de crédito dos seus clientes nos próximos dias."]


def montar_corpo_html(
    grupo: GrupoBanker,
    assinatura: str,
    imagem_src: str,
    aviso_teste: str | None = None,
) -> str:
    bloco = montar_bloco(texto_cartoes(grupo.banker_nome), imagem_src=imagem_src, imagem_largura=LARGURA_IMAGEM)
    return _montar_corpo_html([bloco], assinatura, aviso_teste=aviso_teste)
