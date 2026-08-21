"""Monta o e-mail combinado — saldo + vencimentos do mês — enviado só
no primeiro dia útil do mês. Nos outros dias, main.py manda só o
boletim de saldo normal (src/email_builder.py).
"""

from datetime import date

from .agrupador import GrupoBanker
from .email_base import montar_bloco
from .email_base import montar_corpo_html as _montar_corpo_html
from .email_base import primeiro_nome
from .email_builder_vencimentos import LARGURA_IMAGEM as LARGURA_IMAGEM_VENCIMENTOS
from .email_builder_vencimentos import texto_vencimentos

LARGURA_IMAGEM_SALDO = 640


def montar_corpo_html(
    grupo_saldo: GrupoBanker,
    mes_ref: date,
    assinatura: str,
    imagem_saldo_src: str,
    imagem_vencimentos_src: str | None,
    aviso_teste: str | None = None,
) -> str:
    bloco_saldo = montar_bloco(
        [
            f"Bom dia {primeiro_nome(grupo_saldo.banker_nome)}, tudo bem?",
            "Segue abaixo, o saldo diário referente aos seus clientes no BTG.",
        ],
        imagem_src=imagem_saldo_src,
        imagem_largura=LARGURA_IMAGEM_SALDO,
    )

    textos_vencimentos = texto_vencimentos(grupo_saldo.banker_nome, mes_ref, tem_vencimento=bool(imagem_vencimentos_src))
    # o segundo bloco não repete a saudação — já foi feita no bloco do saldo
    bloco_vencimentos = montar_bloco(
        [f"Hoje também é o primeiro dia útil do mês: {textos_vencimentos[1][0].lower()}{textos_vencimentos[1][1:]}"],
        imagem_src=imagem_vencimentos_src,
        imagem_largura=LARGURA_IMAGEM_VENCIMENTOS,
    )

    return _montar_corpo_html([bloco_saldo, bloco_vencimentos], assinatura, aviso_teste=aviso_teste)
