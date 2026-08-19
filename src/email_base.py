"""HTML base do e-mail — fonte, cores, layout — compartilhado entre o
boletim de saldo e o de vencimentos.
"""

FONTE = "Georgia, 'Times New Roman', Times, serif"
TAMANHO_TEXTO = "11pt"
NAVY = "#0B1F3B"
BRANCO = "#FFFFFF"


def primeiro_nome(nome_completo: str) -> str:
    return nome_completo.split()[0] if nome_completo.strip() else nome_completo


def montar_corpo_html(
    paragrafos: list[str],
    assinatura: str,
    imagem_src: str | None = None,
    imagem_largura: int = 640,
    aviso_teste: str | None = None,
) -> str:
    """Monta o corpo do e-mail: banner de teste (opcional) + parágrafos
    de texto + imagem (opcional, tabela embutida) + assinatura + rodapé
    de confidencialidade. `imagem_src` é `cid:<id>` no envio real, ou
    uma data URI no dry-run; passe `None` quando não há tabela pra
    mostrar (ex: nenhum vencimento no mês).
    """
    banner_teste = (
        f"<p style='background:#fff3cd;padding:8px 12px;border:1px solid #ffe69c;"
        f"font-family:{FONTE};font-size:{TAMANHO_TEXTO};'><b>[MODO TESTE]</b> {aviso_teste}</p>"
        if aviso_teste
        else ""
    )
    paragrafos_html = "".join(f"<p style='font-size:{TAMANHO_TEXTO};'>{p}</p>" for p in paragrafos)
    imagem_html = (
        f"<img src=\"{imagem_src}\" alt=\"Tabela\" width=\"{imagem_largura}\" "
        f"style=\"max-width:{imagem_largura}px;width:100%;height:auto;display:block;border:0;\">"
        if imagem_src
        else ""
    )

    return f"""
    <html>
    <body style="font-family:{FONTE};font-size:{TAMANHO_TEXTO};color:{NAVY};background:{BRANCO};">
      {banner_teste}
      {paragrafos_html}
      {imagem_html}
      <p style="font-size:{TAMANHO_TEXTO};margin-top:20px;">Att,</p>
      <p style="font-size:{TAMANHO_TEXTO};">{assinatura}</p>
      <p style="color:#6B7A94;font-size:{TAMANHO_TEXTO};margin-top:16px;font-style:italic;">
        E-mail gerado automaticamente. Contém informação confidencial — não encaminhe.
      </p>
    </body>
    </html>
    """
