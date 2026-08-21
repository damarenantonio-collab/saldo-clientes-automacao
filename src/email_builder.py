"""Monta o corpo HTML do e-mail de saldo para um único banker.

Estilo: fonte serifada (mais formal, no tom de um family office),
paleta azul-marinho/branco, texto em tamanho 11 padrão. A tabela em si
não é HTML — vem como imagem embutida (veja src/tabela_imagem.py), pra
não poder ser editada por quem recebe o e-mail antes de encaminhar.
"""

from datetime import date

from .agrupador import GrupoBanker
from .email_base import montar_bloco
from .email_base import montar_corpo_html as _montar_corpo_html
from .email_base import primeiro_nome


def montar_corpo_html(
    grupo: GrupoBanker,
    assinatura: str,
    data_referencia: date,
    imagem_src: str,
    aviso_teste: str | None = None,
) -> str:
    """`imagem_src` é o valor do atributo `src` da tabela: `cid:<id>` no
    envio real (imagem anexada inline via notify.py), ou uma data URI
    base64 no dry-run (pra abrir o HTML direto no navegador, sem e-mail
    de verdade por trás).
    """
    bloco = montar_bloco(
        [
            f"Bom dia {primeiro_nome(grupo.banker_nome)}, tudo bem?",
            "Segue abaixo, o saldo diário referente aos seus clientes no BTG.",
        ],
        imagem_src=imagem_src,
        imagem_largura=640,
    )
    return _montar_corpo_html([bloco], assinatura, aviso_teste=aviso_teste)
