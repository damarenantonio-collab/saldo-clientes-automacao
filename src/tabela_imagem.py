"""Desenha a tabela de saldo como imagem PNG, em vez de HTML.

Objetivo: uma tabela em texto/HTML pode ser editada por quem recebe o
e-mail antes de encaminhar (célula, valor, linha inteira); como imagem,
isso deixa de ser possível — o conteúdo fica travado exatamente como a
automação gerou.
"""

from io import BytesIO

from PIL import Image, ImageDraw

from .agrupador import GrupoBanker
from .imagem_util import (
    BRANCO,
    FONTES_BOLD,
    FONTES_REGULAR,
    NAVY,
    NAVY_CLARO,
    VERMELHO,
    carregar_fonte,
    escrever,
    fmt_moeda,
)

LARGURA = 640
ALTURA_LINHA = 38
ALTURA_FAIXA = 42  # cabeçalho e rodapé (total)
PADDING_X = 14
COL_CLIENTE = int(LARGURA * 0.32)
COL_CONTA = int(LARGURA * 0.32)


def gerar_png(grupo: GrupoBanker, tamanho_fonte: int = 14) -> bytes:
    fonte = carregar_fonte(FONTES_REGULAR, tamanho_fonte)
    fonte_bold = carregar_fonte(FONTES_BOLD, tamanho_fonte)

    n_linhas = len(grupo.clientes)
    altura = ALTURA_FAIXA + n_linhas * ALTURA_LINHA + ALTURA_FAIXA

    img = Image.new("RGB", (LARGURA, altura), BRANCO)
    draw = ImageDraw.Draw(img)
    margem_direita = LARGURA - PADDING_X

    draw.rectangle([0, 0, LARGURA - 1, ALTURA_FAIXA - 1], fill=NAVY)
    escrever(draw, PADDING_X, 0, ALTURA_FAIXA, "CLIENTE", fonte_bold, BRANCO)
    escrever(draw, COL_CLIENTE + PADDING_X, 0, ALTURA_FAIXA, "CONTA", fonte_bold, BRANCO)
    escrever(draw, 0, 0, ALTURA_FAIXA, "SALDO", fonte_bold, BRANCO, alinhar_direita_em=margem_direita)

    y = ALTURA_FAIXA
    for _, row in grupo.clientes.iterrows():
        y0, y1 = y, y + ALTURA_LINHA
        cor_saldo = VERMELHO if row["saldo"] < 0 else NAVY
        escrever(draw, PADDING_X, y0, y1, str(row["cliente"]), fonte, NAVY)
        escrever(draw, COL_CLIENTE + PADDING_X, y0, y1, str(row["conta"]), fonte, NAVY)
        escrever(draw, 0, y0, y1, fmt_moeda(row["saldo"]), fonte_bold if row["saldo"] < 0 else fonte, cor_saldo, alinhar_direita_em=margem_direita)
        draw.line([(0, y1 - 1), (LARGURA, y1 - 1)], fill=NAVY_CLARO, width=1)
        y = y1

    y0, y1 = y, y + ALTURA_FAIXA
    draw.rectangle([0, y0, LARGURA - 1, y1 - 1], fill=NAVY)
    total = grupo.clientes["saldo"].sum()
    escrever(draw, PADDING_X, y0, y1, f"Total ({n_linhas} cliente(s))", fonte_bold, BRANCO)
    escrever(draw, 0, y0, y1, fmt_moeda(total), fonte_bold, BRANCO, alinhar_direita_em=margem_direita)

    draw.rectangle([0, 0, LARGURA - 1, altura - 1], outline=NAVY, width=1)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
