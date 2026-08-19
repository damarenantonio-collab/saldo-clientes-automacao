"""Desenha a tabela de saldo como imagem PNG, em vez de HTML.

Objetivo: uma tabela em texto/HTML pode ser editada por quem recebe o
e-mail antes de encaminhar (célula, valor, linha inteira); como imagem,
isso deixa de ser possível — o conteúdo fica travado exatamente como a
automação gerou.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .agrupador import GrupoBanker

NAVY = (11, 31, 59)  # #0B1F3B
NAVY_CLARO = (217, 223, 234)  # #D9DFEA
BRANCO = (255, 255, 255)

LARGURA = 640
ALTURA_LINHA = 38
ALTURA_FAIXA = 42  # cabeçalho e rodapé (total)
PADDING_X = 14
COL_CLIENTE = int(LARGURA * 0.32)
COL_CONTA = int(LARGURA * 0.32)

# Georgia é a mesma fonte usada no texto do e-mail e vem com o Windows/
# Office por padrão. Se não existir (ex: rodando fora do Windows), cai
# pro DejaVu Serif (Linux) e, por último, pra fonte padrão do Pillow.
FONTES_REGULAR = [
    "C:/Windows/Fonts/georgia.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]
FONTES_BOLD = [
    "C:/Windows/Fonts/georgiab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]


def _carregar_fonte(caminhos: list[str], tamanho: int) -> ImageFont.FreeTypeFont:
    for caminho in caminhos:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(size=tamanho)


def _fmt_moeda(valor: float) -> str:
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def _escrever(draw, x, y0, y1, texto, fonte, cor, alinhar_direita_em=None):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    altura_texto = bbox[3] - bbox[1]
    y = y0 + ((y1 - y0) - altura_texto) / 2 - bbox[1]
    if alinhar_direita_em is not None:
        largura_texto = bbox[2] - bbox[0]
        draw.text((alinhar_direita_em - largura_texto, y), texto, font=fonte, fill=cor)
    else:
        draw.text((x, y), texto, font=fonte, fill=cor)


def gerar_png(grupo: GrupoBanker, tamanho_fonte: int = 14) -> bytes:
    fonte = _carregar_fonte(FONTES_REGULAR, tamanho_fonte)
    fonte_bold = _carregar_fonte(FONTES_BOLD, tamanho_fonte)

    n_linhas = len(grupo.clientes)
    altura = ALTURA_FAIXA + n_linhas * ALTURA_LINHA + ALTURA_FAIXA

    img = Image.new("RGB", (LARGURA, altura), BRANCO)
    draw = ImageDraw.Draw(img)
    margem_direita = LARGURA - PADDING_X

    draw.rectangle([0, 0, LARGURA - 1, ALTURA_FAIXA - 1], fill=NAVY)
    _escrever(draw, PADDING_X, 0, ALTURA_FAIXA, "CLIENTE", fonte_bold, BRANCO)
    _escrever(draw, COL_CLIENTE + PADDING_X, 0, ALTURA_FAIXA, "CONTA", fonte_bold, BRANCO)
    _escrever(draw, 0, 0, ALTURA_FAIXA, "SALDO", fonte_bold, BRANCO, alinhar_direita_em=margem_direita)

    y = ALTURA_FAIXA
    for _, row in grupo.clientes.iterrows():
        y0, y1 = y, y + ALTURA_LINHA
        _escrever(draw, PADDING_X, y0, y1, str(row["cliente"]), fonte, NAVY)
        _escrever(draw, COL_CLIENTE + PADDING_X, y0, y1, str(row["conta"]), fonte, NAVY)
        _escrever(draw, 0, y0, y1, _fmt_moeda(row["saldo"]), fonte, NAVY, alinhar_direita_em=margem_direita)
        draw.line([(0, y1 - 1), (LARGURA, y1 - 1)], fill=NAVY_CLARO, width=1)
        y = y1

    y0, y1 = y, y + ALTURA_FAIXA
    draw.rectangle([0, y0, LARGURA - 1, y1 - 1], fill=NAVY)
    total = grupo.clientes["saldo"].sum()
    _escrever(draw, PADDING_X, y0, y1, f"Total ({n_linhas} cliente(s))", fonte_bold, BRANCO)
    _escrever(draw, 0, y0, y1, _fmt_moeda(total), fonte_bold, BRANCO, alinhar_direita_em=margem_direita)

    draw.rectangle([0, 0, LARGURA - 1, altura - 1], outline=NAVY, width=1)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
