"""HTML base do e-mail — fonte, cores, layout — compartilhado entre o
boletim de saldo, o de vencimentos e o combinado dos dois.
"""

FONTE = "Georgia, 'Times New Roman', Times, serif"
TAMANHO_TEXTO = "11pt"
NAVY = "#0B1F3B"
BRANCO = "#FFFFFF"


def primeiro_nome(nome_completo: str) -> str:
    return nome_completo.split()[0] if nome_completo.strip() else nome_completo


def montar_bloco(paragrafos: list[str], imagem_src: str | None = None, imagem_largura: int = 640) -> dict:
    return {"paragrafos": paragrafos, "imagem_src": imagem_src, "imagem_largura": imagem_largura}


def montar_corpo_html(
    blocos: list[dict],
    assinatura: str,
    aviso_teste: str | None = None,
) -> str:
    """Monta o corpo do e-mail: banner de teste (opcional) + um ou mais
    `blocos` (cada um com seus parágrafos de texto e, opcionalmente, uma
    imagem — tabela embutida) + assinatura + rodapé de confidencialidade.

    Cada `imagem_src` é `cid:<id>` no envio real, ou uma data URI no
    dry-run; `None` quando não há tabela pra mostrar naquele bloco (ex:
    nenhum vencimento no mês) — nesse caso só o texto do bloco aparece.
    """
    banner_teste = (
        f"<p style='background:#fff3cd;padding:8px 12px;border:1px solid #ffe69c;"
        f"font-family:{FONTE};font-size:{TAMANHO_TEXTO};'><b>[MODO TESTE]</b> {aviso_teste}</p>"
        if aviso_teste
        else ""
    )

    blocos_html = ""
    for bloco in blocos:
        paragrafos_html = "".join(f"<p style='font-size:{TAMANHO_TEXTO};'>{p}</p>" for p in bloco["paragrafos"])
        imagem_src = bloco.get("imagem_src")
        largura = bloco.get("imagem_largura", 640)
        imagem_html = (
            f"<img src=\"{imagem_src}\" alt=\"Tabela\" width=\"{largura}\" "
            f"style=\"max-width:{largura}px;width:100%;height:auto;display:block;border:0;margin-bottom:20px;\">"
            if imagem_src
            else ""
        )
        blocos_html += paragrafos_html + imagem_html

    return f"""
    <html>
    <body style="font-family:{FONTE};font-size:{TAMANHO_TEXTO};color:{NAVY};background:{BRANCO};">
      {banner_teste}
      {blocos_html}
      <p style="font-size:{TAMANHO_TEXTO};margin-top:4px;">Att,</p>
      <p style="font-size:{TAMANHO_TEXTO};">{assinatura}</p>
      <p style="color:#6B7A94;font-size:{TAMANHO_TEXTO};margin-top:16px;font-style:italic;">
        E-mail gerado automaticamente. Contém informação confidencial — não encaminhe.
      </p>
    </body>
    </html>
    """
