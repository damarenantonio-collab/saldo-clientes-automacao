"""Desenha a tabela de vencimento de fatura de cartão de crédito como
imagem PNG (mesmo princípio de src/tabela_imagem.py: imagem em vez de
HTML editável).
"""

from io import BytesIO

from PIL import Image, ImageDraw

from .agrupador import GrupoBanker
from .imagem_util import BRANCO, FONTES_BOLD, FONTES_REGULAR, NAVY, NAVY_CLARO, carregar_fonte, escrever, truncar

LARGURA = 640
ALTURA_LINHA = 36
ALTURA_FAIXA = 40
PADDING_X = 10

COL_CLIENTE = 0
COL_CARTAO = 160
COL_DIA = 420

LARGURA_CARTAO = COL_DIA - COL_CARTAO - PADDING_X


def texto_vence_em(dias: int) -> str:
    if dias <= 0:
        return "HOJE"
    if dias == 1:
        return "AMANHÃ"
    return f"em {dias} dias"


def gerar_png(grupo: GrupoBanker, tamanho_fonte: int = 12) -> bytes:
    fonte = carregar_fonte(FONTES_REGULAR, tamanho_fonte)
    fonte_bold = carregar_fonte(FONTES_BOLD, tamanho_fonte)

    n_linhas = len(grupo.clientes)
    altura = ALTURA_FAIXA + n_linhas * ALTURA_LINHA

    img = Image.new("RGB", (LARGURA, altura), BRANCO)
    draw = ImageDraw.Draw(img)
    margem_direita = LARGURA - PADDING_X

    draw.rectangle([0, 0, LARGURA - 1, ALTURA_FAIXA - 1], fill=NAVY)
    escrever(draw, COL_CLIENTE + PADDING_X, 0, ALTURA_FAIXA, "CLIENTE", fonte_bold, BRANCO)
    escrever(draw, COL_CARTAO + PADDING_X, 0, ALTURA_FAIXA, "CARTÃO", fonte_bold, BRANCO)
    escrever(draw, COL_DIA + PADDING_X, 0, ALTURA_FAIXA, "DIA", fonte_bold, BRANCO)
    escrever(draw, 0, 0, ALTURA_FAIXA, "VENCE", fonte_bold, BRANCO, alinhar_direita_em=margem_direita)

    y = ALTURA_FAIXA
    for _, row in grupo.clientes.iterrows():
        y0, y1 = y, y + ALTURA_LINHA
        escrever(draw, COL_CLIENTE + PADDING_X, y0, y1, str(row["cliente"]), fonte, NAVY)
        escrever(
            draw, COL_CARTAO + PADDING_X, y0, y1, truncar(draw, str(row["cartao"]), fonte, LARGURA_CARTAO), fonte, NAVY
        )
        escrever(draw, COL_DIA + PADDING_X, y0, y1, f"dia {int(row['dia_vencimento']):02d}", fonte, NAVY)
        escrever(
            draw, 0, y0, y1, texto_vence_em(int(row["dias_ate_vencer"])), fonte, NAVY, alinhar_direita_em=margem_direita
        )
        draw.line([(0, y1 - 1), (LARGURA, y1 - 1)], fill=NAVY_CLARO, width=1)
        y = y1

    draw.rectangle([0, 0, LARGURA - 1, altura - 1], outline=NAVY, width=1)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
