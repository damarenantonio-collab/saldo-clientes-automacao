"""Envia por e-mail o saldo em conta dos clientes do family office — um
e-mail por banker, contendo apenas os clientes daquele banker.

Uso:
    python main.py [--config config/settings.yaml]
    python main.py --dry-run     # não envia nada; grava o HTML de cada
                                  # banker em saida_teste/ pra conferir
"""

import argparse
import logging
import sys
import traceback
from datetime import date
from pathlib import Path

import yaml

from src import agrupador, bankers, email_builder, history_log, notify, saldos

ROOT = Path(__file__).resolve().parent


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "execucao.log", encoding="utf-8"),
        ],
    )
    return logging.getLogger(__name__)


def load_settings(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(settings: dict, logger: logging.Logger, dry_run: bool) -> None:
    saldos_xlsx = (ROOT / settings["saldos_xlsx"]).resolve()
    bankers_csv = (ROOT / settings["bankers_csv"]).resolve()
    banker_padrao = settings["banker_padrao"]
    sheet_name = settings.get("saldos_sheet", saldos.SHEET_PADRAO)

    if not saldos_xlsx.exists():
        raise RuntimeError(
            f"{saldos_xlsx} não encontrado. Aponte saldos_xlsx em settings.yaml para "
            f"o Excel de saldo em conta baixado do BTG."
        )
    if not bankers_csv.exists():
        raise RuntimeError(
            f"{bankers_csv} não encontrado. Copie config/bankers.example.csv para "
            f"config/bankers.csv e preencha com seus bankers."
        )

    df_saldos = saldos.load_saldos(saldos_xlsx, banker_padrao, sheet_name=sheet_name)
    mapa_bankers = bankers.load_bankers(bankers_csv)
    log_sensivel = settings.get("log_dados_sensiveis", False)

    logger.info(
        "Carregado(s) %d conta(s) de cliente da aba '%s'.",
        len(df_saldos),
        sheet_name,
    )

    grupos, pendentes = agrupador.agrupar_por_banker(df_saldos, mapa_bankers)

    if pendentes:
        notify.send_alert(
            settings,
            subject=f"[Saldo Clientes] {len(pendentes)} banker(s) sem e-mail cadastrado",
            body=(
                f"Os banker_id(s) abaixo aparecem em saldos.csv mas não têm e-mail "
                f"cadastrado em bankers.csv — os clientes deles NÃO foram enviados "
                f"nesta execução:\n\n" + "\n".join(f"- {b}" for b in pendentes)
            ),
        )

    if not grupos:
        logger.warning("Nenhum grupo de banker pronto para envio nesta execução.")
        return

    data_ref = date.today()
    assinatura = settings["assinatura"]
    assunto_template = settings.get("assunto_template", "Saldo em Conta - {data}")

    saida_teste = ROOT / "saida_teste"
    falhas = []

    for grupo in grupos:
        qtd = len(grupo.clientes)
        total = grupo.clientes["saldo"].sum()
        if log_sensivel:
            logger.info("Banker %s (%s): %d cliente(s), total R$ %.2f.", grupo.banker_nome, grupo.email, qtd, total)
        else:
            logger.info("Banker %s: %d cliente(s).", grupo.banker_nome, qtd)

        subject = assunto_template.format(banker=grupo.banker_nome, data=data_ref.strftime("%d/%m/%Y"))

        if dry_run:
            html_body = email_builder.montar_corpo_html(grupo, assinatura, data_ref)
            saida_teste.mkdir(parents=True, exist_ok=True)
            destino = saida_teste / f"{grupo.banker_id}.html"
            destino.write_text(html_body, encoding="utf-8")
            logger.info("[DRY-RUN] E-mail de %s gravado em %s (nada foi enviado).", grupo.banker_nome, destino)
            continue

        try:
            notify.enviar_email_banker(
                settings["email"],
                grupo,
                subject,
                lambda aviso, g=grupo: email_builder.montar_corpo_html(g, assinatura, data_ref, aviso_teste=aviso),
            )
        except Exception as exc:
            logger.error("Falha ao enviar e-mail para banker %s: %s", grupo.banker_id, exc, exc_info=True)
            falhas.append(grupo.banker_id)

    if falhas:
        notify.send_alert(
            settings,
            subject=f"[Saldo Clientes] Falha ao enviar e-mail para {len(falhas)} banker(s)",
            body=(
                f"Falha ao enviar o e-mail de saldo para os banker_id(s) abaixo. "
                f"Veja logs/execucao.log para detalhes:\n\n" + "\n".join(f"- {b}" for b in falhas)
            ),
        )

    if not dry_run and settings.get("manter_historico", True):
        history_path = ROOT / settings.get("historico_path", "historico/envios_diarios.csv")
        history_log.append_snapshot(grupos, data_ref, history_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config/settings.yaml", help="Caminho do settings.yaml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não envia nenhum e-mail; grava o HTML de cada banker em saida_teste/ para conferência.",
    )
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve()
    if not config_path.exists():
        print(
            f"Arquivo de configuração não encontrado: {config_path}\n"
            f"Copie config/settings.example.yaml para settings.yaml e ajuste os valores."
        )
        sys.exit(1)

    settings = load_settings(config_path)
    logger = setup_logging(ROOT / "logs")

    try:
        run(settings, logger, dry_run=args.dry_run)
    except Exception:
        logger.error("Falha na execução:\n%s", traceback.format_exc())
        notify.send_alert(
            settings,
            subject="[Saldo Clientes] Falha na execução",
            body=f"A execução de hoje falhou com o erro:\n\n{traceback.format_exc()}",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
