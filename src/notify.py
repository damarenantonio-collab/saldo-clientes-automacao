"""Envio dos e-mails (um por banker) e alertas de falha por SMTP.

Usa SMTP simples — funciona com Gmail usando uma "senha de app" (não a
senha normal da conta; crie uma em myaccount.google.com/apppasswords), ou
com o SMTP corporativo da empresa (host/porta/usuário/senha próprios).

Cada e-mail é enviado individualmente, com "To" contendo só o e-mail
daquele banker — nunca em lote/CC/BCC com outros bankers juntos.
"""

import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .agrupador import GrupoBanker

logger = logging.getLogger(__name__)


def _smtp_send(
    cfg: dict,
    destinatario: str,
    subject: str,
    html_body: str,
    imagens: list[tuple[bytes, str]] | None = None,
    anexos: list[tuple[bytes, str]] | None = None,
) -> None:
    """`imagens` é uma lista de (png_bytes, cid) — uma por tabela embutida
    no e-mail (o boletim combinado tem duas: saldo e vencimentos).
    `anexos` é uma lista de (xlsx_bytes, nome_arquivo) — anexo de verdade,
    não embutido no corpo."""
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = cfg["remetente"]
    msg["To"] = destinatario

    corpo = MIMEMultipart("related")
    alternativo = MIMEMultipart("alternative")
    alternativo.attach(MIMEText(html_body, "html", "utf-8"))
    corpo.attach(alternativo)

    for imagem_png, cid in imagens or []:
        imagem = MIMEImage(imagem_png)
        imagem.add_header("Content-ID", f"<{cid}>")
        imagem.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
        corpo.attach(imagem)

    msg.attach(corpo)

    for anexo_bytes, nome_arquivo in anexos or []:
        anexo = MIMEApplication(
            anexo_bytes, _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        anexo.add_header("Content-Disposition", "attachment", filename=nome_arquivo)
        msg.attach(anexo)

    host = cfg.get("smtp_host", "smtp.gmail.com")
    port = int(cfg.get("smtp_port", 587))

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(cfg["remetente"], cfg["senha"])
        server.sendmail(cfg["remetente"], [destinatario], msg.as_string())


def enviar_email_banker(
    email_cfg: dict,
    grupo: GrupoBanker,
    subject: str,
    imagens: list[tuple[bytes, str]],
    html_body_factory,
    anexos: list[tuple[bytes, str]] | None = None,
) -> None:
    """Envia (ou simula, em modo teste) o e-mail de um banker.

    `html_body_factory(aviso_teste)` monta o corpo (referenciando cada
    tabela como `cid:<cid>`, usando o mesmo `cid` passado em `imagens`)
    — recebe o aviso a exibir no topo quando em modo teste, ou None em
    envio real. `imagens=[]` quando não há tabela nenhuma pra anexar.
    `anexos` é uma lista de (xlsx_bytes, nome_arquivo) — anexo de
    verdade (não embutido no corpo), com os mesmos dados da tabela.
    """
    modo_teste = (email_cfg.get("modo_teste") or {}).get("ativo", False)

    if modo_teste:
        destino_real = grupo.email
        destinatario = email_cfg["modo_teste"]["enviar_para"]
        aviso = f"Este e-mail seria enviado para {grupo.banker_nome} &lt;{destino_real}&gt;."
    else:
        destinatario = grupo.email
        aviso = None

    html_body = html_body_factory(aviso)
    _smtp_send(email_cfg, destinatario, subject, html_body, imagens=imagens, anexos=anexos)
    logger.info(
        "E-mail enviado: banker=%s destinatario=%s modo_teste=%s",
        grupo.banker_id,
        destinatario,
        modo_teste,
    )


def send_alert(settings: dict, subject: str, body: str) -> None:
    """Envia um e-mail de alerta pro(s) responsável(is) pela automação, se
    `alerta_email.ativo` estiver configurado.

    Nunca inclui dados de cliente no corpo — só descrição do problema.
    Nunca levanta exceção — uma falha ao enviar o alerta não pode derrubar
    a execução principal, só fica registrada no log.
    """
    alerta_cfg = (settings or {}).get("alerta_email") or {}
    if not alerta_cfg.get("ativo"):
        return

    email_cfg = (settings or {}).get("email") or {}
    required = ["remetente", "senha"]
    missing = [k for k in required if not email_cfg.get(k)] + (["alerta_email.para"] if not alerta_cfg.get("para") else [])
    if missing:
        logger.warning("alerta_email.ativo=true mas faltam campos: %s. Alerta não enviado.", missing)
        return

    try:
        _smtp_send(email_cfg, alerta_cfg["para"], subject, f"<pre>{body}</pre>")
        logger.info("Alerta enviado por e-mail para %s.", alerta_cfg["para"])
    except Exception as exc:
        logger.warning("Falha ao enviar alerta por e-mail: %s", exc)
