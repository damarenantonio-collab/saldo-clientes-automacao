"""Monta o corpo HTML do e-mail de saldo para um único banker.

Estilo: fonte serifada (mais formal, no tom de um family office),
paleta azul-marinho/branco, texto em tamanho 11 padrão. A tabela em si
não é HTML — vem como imagem embutida (veja src/tabela_imagem.py), pra
não poder ser editada por quem recebe o e-mail antes de encaminhar.
Tudo em CSS inline — clientes de e-mail (Outlook em especial) ignoram
<style> e @font-face, então cada elemento carrega seu próprio estilo.
"""

from datetime import date

from .agrupador import GrupoBanker

FONTE = "Georgia, 'Times New Roman', Times, serif"
TAMANHO_TEXTO = "11pt"
NAVY = "#0B1F3B"
BRANCO = "#FFFFFF"


def _primeiro_nome(nome_completo: str) -> str:
    return nome_completo.split()[0] if nome_completo.strip() else nome_completo


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
    banner_teste = (
        f"<p style='background:#fff3cd;padding:8px 12px;border:1px solid #ffe69c;"
        f"font-family:{FONTE};font-size:{TAMANHO_TEXTO};'><b>[MODO TESTE]</b> {aviso_teste}</p>"
        if aviso_teste
        else ""
    )

    return f"""
    <html>
    <body style="font-family:{FONTE};font-size:{TAMANHO_TEXTO};color:{NAVY};background:{BRANCO};">
      {banner_teste}
      <p style="font-size:{TAMANHO_TEXTO};">Bom dia {_primeiro_nome(grupo.banker_nome)}, tudo bem?</p>
      <p style="font-size:{TAMANHO_TEXTO};">Segue abaixo, o saldo diário referente aos seus clientes no BTG.</p>
      <img src="{imagem_src}" alt="Saldo em conta dos clientes" width="640"
           style="max-width:640px;width:100%;height:auto;display:block;border:0;">
      <p style="font-size:{TAMANHO_TEXTO};margin-top:20px;">Att,</p>
      <p style="font-size:{TAMANHO_TEXTO};">{assinatura}</p>
      <p style="color:#6B7A94;font-size:{TAMANHO_TEXTO};margin-top:16px;font-style:italic;">
        E-mail gerado automaticamente. Contém informação confidencial — não encaminhe.
      </p>
    </body>
    </html>
    """
