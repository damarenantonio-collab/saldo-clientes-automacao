"""Monta o corpo HTML do e-mail de saldo para um único banker."""

from datetime import date

from .agrupador import GrupoBanker


def _fmt_moeda(valor: float) -> str:
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def _primeiro_nome(nome_completo: str) -> str:
    return nome_completo.split()[0] if nome_completo.strip() else nome_completo


def montar_corpo_html(
    grupo: GrupoBanker,
    assinatura: str,
    data_referencia: date,
    aviso_teste: str | None = None,
) -> str:
    linhas = "".join(
        f"<tr>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #e5e5e5;'>{cliente}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #e5e5e5;'>{conta}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #e5e5e5;text-align:right;'>{_fmt_moeda(saldo)}</td>"
        f"</tr>"
        for cliente, conta, saldo in zip(
            grupo.clientes["cliente"], grupo.clientes["conta"], grupo.clientes["saldo"]
        )
    )

    total = grupo.clientes["saldo"].sum()
    banner_teste = (
        f"<p style='background:#fff3cd;padding:8px 12px;border:1px solid #ffe69c;'>"
        f"<b>[MODO TESTE]</b> {aviso_teste}</p>"
        if aviso_teste
        else ""
    )

    return f"""
    <html>
    <body style="font-family:Arial,Helvetica,sans-serif;color:#222;">
      {banner_teste}
      <p>Bom dia {_primeiro_nome(grupo.banker_nome)}, tudo bem?</p>
      <p>Segue abaixo, o saldo diário referente aos seus clientes no BTG.</p>
      <table style="border-collapse:collapse;width:100%;max-width:640px;">
        <thead>
          <tr style="background:#f2f2f2;">
            <th style="padding:6px 10px;text-align:left;">Cliente (código)</th>
            <th style="padding:6px 10px;text-align:left;">Conta</th>
            <th style="padding:6px 10px;text-align:right;">Saldo</th>
          </tr>
        </thead>
        <tbody>
          {linhas}
        </tbody>
        <tfoot>
          <tr style="font-weight:bold;">
            <td style="padding:8px 10px;" colspan="2">Total ({len(grupo.clientes)} cliente(s))</td>
            <td style="padding:8px 10px;text-align:right;">{_fmt_moeda(total)}</td>
          </tr>
        </tfoot>
      </table>
      <p style="margin-top:20px;">Att,</p>
      <p>{assinatura}</p>
      <p style="color:#777;font-size:12px;margin-top:16px;">
        E-mail gerado automaticamente. Contém informação confidencial — não encaminhe.
      </p>
    </body>
    </html>
    """
