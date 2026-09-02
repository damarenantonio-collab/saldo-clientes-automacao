"""Utilidades compartilhadas pra desenhar tabelas como imagem PNG —
usado tanto pelo boletim de saldo quanto pelo de vencimentos. Mesma
paleta azul-marinho/branco e fonte Georgia dos e-mails.
"""

from pathlib import Path

from PIL import ImageFont

NAVY = (11, 31, 59)  # #0B1F3B
NAVY_CLARO = (217, 223, 234)  # #D9DFEA
BRANCO = (255, 255, 255)
VERMELHO = (198, 40, 40)  # #C62828 — alerta de saldo negativo

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


def carregar_fonte(caminhos: list[str], tamanho: int) -> ImageFont.FreeTypeFont:
    for caminho in caminhos:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(size=tamanho)


def fmt_moeda(valor: float) -> str:
    sinal = "-" if valor < 0 else ""
    texto = f"{abs(valor):,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{sinal}R$ {texto}"


def escrever(draw, x, y0, y1, texto, fonte, cor, alinhar_direita_em=None):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    altura_texto = bbox[3] - bbox[1]
    y = y0 + ((y1 - y0) - altura_texto) / 2 - bbox[1]
    if alinhar_direita_em is not None:
        largura_texto = bbox[2] - bbox[0]
        draw.text((alinhar_direita_em - largura_texto, y), texto, font=fonte, fill=cor)
    else:
        draw.text((x, y), texto, font=fonte, fill=cor)


def truncar(draw, texto, fonte, largura_max) -> str:
    """Encurta `texto` com "…" no final se não couber em `largura_max`
    pixels — usado pra colunas como Emissor, que podem ter nomes longos.
    """
    if draw.textlength(texto, font=fonte) <= largura_max:
        return texto
    reticencias = "…"
    cortado = texto
    while cortado and draw.textlength(cortado + reticencias, font=fonte) > largura_max:
        cortado = cortado[:-1]
    return cortado + reticencias if cortado else reticencias
