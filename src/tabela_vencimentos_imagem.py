"""Desenha a tabela de vencimentos do mês como imagem PNG (mesmo
princípio de src/tabela_imagem.py: imagem em vez de HTML editável).
"""

from io import BytesIO

from PIL import Image, ImageDraw

from .agrupador import GrupoBanker
from .imagem_util import BRANCO, FONTES_BOLD, FONTES_REGULAR, NAVY, NAVY_CLARO, carregar_fonte, escrever, fmt_moeda, truncar

LARGURA = 760
ALTURA_LINHA = 36
ALTURA_FAIXA = 40
PADDING_X = 10

COL_CLIENTE = 0
COL_ATIVO = 90
COL_EMISSOR = 250
COL_VENCIMENTO = 470
# da COL_VENCIMENTO até a margem direita fica o espaço do valor
# (alinhado à direita) — medido com Pillow pra não sobrepor o
# cabeçalho "VENCIMENTO" (97px) com "VALOR LÍQUIDO" (112px)

LARGURA_ATIVO = COL_EMISSOR - COL_ATIVO - PADDING_X
LARGURA_EMISSOR = COL_VENCIMENTO - COL_EMISSOR - PADDING_X


def gerar_png(grupo: GrupoBanker, tamanho_fonte: int = 12) -> bytes:
    fonte = carregar_fonte(FONTES_REGULAR, tamanho_fonte)
    fonte_bold = carregar_fonte(FONTES_BOLD, tamanho_fonte)

    n_linhas = len(grupo.clientes)
    altura = ALTURA_FAIXA + n_linhas * ALTURA_LINHA + ALTURA_FAIXA

    img = Image.new("RGB", (LARGURA, altura), BRANCO)
    draw = ImageDraw.Draw(img)
    margem_direita = LARGURA - PADDING_X

    draw.rectangle([0, 0, LARGURA - 1, ALTURA_FAIXA - 1], fill=NAVY)
    escrever(draw, COL_CLIENTE + PADDING_X, 0, ALTURA_FAIXA, "CLIENTE", fonte_bold, BRANCO)
    escrever(draw, COL_ATIVO + PADDING_X, 0, ALTURA_FAIXA, "ATIVO", fonte_bold, BRANCO)
    escrever(draw, COL_EMISSOR + PADDING_X, 0, ALTURA_FAIXA, "EMISSOR", fonte_bold, BRANCO)
    escrever(draw, COL_VENCIMENTO + PADDING_X, 0, ALTURA_FAIXA, "VENCIMENTO", fonte_bold, BRANCO)
    escrever(draw, 0, 0, ALTURA_FAIXA, "VALOR LÍQUIDO", fonte_bold, BRANCO, alinhar_direita_em=margem_direita)

    y = ALTURA_FAIXA
    for _, row in grupo.clientes.iterrows():
        y0, y1 = y, y + ALTURA_LINHA
        escrever(draw, COL_CLIENTE + PADDING_X, y0, y1, str(row["cliente"]), fonte, NAVY)
        escrever(draw, COL_ATIVO + PADDING_X, y0, y1, truncar(draw, str(row["ativo"]), fonte, LARGURA_ATIVO), fonte, NAVY)
        escrever(
            draw, COL_EMISSOR + PADDING_X, y0, y1, truncar(draw, str(row["emissor"]), fonte, LARGURA_EMISSOR), fonte, NAVY
        )
        escrever(draw, COL_VENCIMENTO + PADDING_X, y0, y1, row["vencimento"].strftime("%d/%m/%Y"), fonte, NAVY)
        escrever(draw, 0, y0, y1, fmt_moeda(row["valor_liquido"]), fonte, NAVY, alinhar_direita_em=margem_direita)
        draw.line([(0, y1 - 1), (LARGURA, y1 - 1)], fill=NAVY_CLARO, width=1)
        y = y1

    y0, y1 = y, y + ALTURA_FAIXA
    draw.rectangle([0, y0, LARGURA - 1, y1 - 1], fill=NAVY)
    total = grupo.clientes["valor_liquido"].sum()
    escrever(draw, PADDING_X, y0, y1, f"Total ({n_linhas} vencimento(s))", fonte_bold, BRANCO)
    escrever(draw, 0, y0, y1, fmt_moeda(total), fonte_bold, BRANCO, alinhar_direita_em=margem_direita)

    draw.rectangle([0, 0, LARGURA - 1, altura - 1], outline=NAVY, width=1)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
