"""Monta o corpo HTML do e-mail de saldo para um único banker.

Estilo: fonte serifada (mais formal, no tom de um family office),
paleta azul-marinho/branco, texto em tamanho 11 padrão. As tabelas em
si não são HTML — vêm como imagem embutida (veja src/tabela_imagem.py),
pra não poderem ser editadas por quem recebe o e-mail antes de
encaminhar.

O e-mail traz até duas tabelas — Investimentos e Banking — cada uma
com sua própria imagem. Quando um banker não tem cliente numa das
duas categorias, a tabela correspondente simplesmente não aparece
(sem aviso de "vazio", pra manter o e-mail limpo).
"""

from datetime import date

from .email_base import montar_bloco
from .email_base import montar_corpo_html as _montar_corpo_html
from .email_base import primeiro_nome


def montar_corpo_html(
    banker_nome: str,
    assinatura: str,
    data_referencia: date,
    investimentos_src: str | None,
    banking_src: str | None,
    aviso_teste: str | None = None,
) -> str:
    """`investimentos_src`/`banking_src` são o valor do atributo `src`
    de cada tabela: `cid:<id>` no envio real (imagem anexada inline via
    notify.py), uma data URI base64 no dry-run, ou `None` quando o
    banker não tem cliente naquela categoria (tabela omitida)."""
    blocos = [
        montar_bloco(
            [
                f"Bom dia {primeiro_nome(banker_nome)}, tudo bem?",
                "Segue abaixo, o saldo diário referente aos seus clientes no BTG.",
            ]
        )
    ]
    if investimentos_src:
        blocos.append(montar_bloco(["<b>Investimentos</b>"], imagem_src=investimentos_src, imagem_largura=640))
    if banking_src:
        blocos.append(montar_bloco(["<b>Banking</b>"], imagem_src=banking_src, imagem_largura=640))

    return _montar_corpo_html(blocos, assinatura, aviso_teste=aviso_teste)
