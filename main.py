"""Envia por e-mail o saldo em conta dos clientes do family office — um
e-mail por banker, contendo apenas os clientes daquele banker, com uma
tabela de Investimentos e uma de Banking.

Uso:
    python main.py [--config config/settings.yaml]
    python main.py --dry-run     # não envia nada; grava o HTML de cada
                                  # banker em saida_teste/ pra conferir
"""

import argparse
import base64
import logging
import sys
import traceback
from datetime import date
from pathlib import Path

import yaml

from src import agrupador, bankers, email_builder, history_log, notify, saldos, tabela_imagem

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
    sheet_investimentos = settings.get("saldos_sheet_investimentos", saldos.SHEET_INVESTIMENTOS_PADRAO)
    sheet_banking = settings.get("saldos_sheet_banking", saldos.SHEET_BANKING_PADRAO)

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

    df_investimentos = saldos.load_saldos(saldos_xlsx, sheet_name=sheet_investimentos)
    df_banking = saldos.load_saldos(saldos_xlsx, sheet_name=sheet_banking)
    mapa_bankers = bankers.load_bankers(bankers_csv)
    log_sensivel = settings.get("log_dados_sensiveis", False)

    logger.info(
        "Carregado(s) %d conta(s) de cliente da aba '%s' e %d da aba '%s'.",
        len(df_investimentos),
        sheet_investimentos,
        len(df_banking),
        sheet_banking,
    )

    grupos_investimentos, pendentes_investimentos = agrupador.agrupar_por_banker(df_investimentos, mapa_bankers)
    grupos_banking, pendentes_banking = agrupador.agrupar_por_banker(df_banking, mapa_bankers)

    pendentes = sorted(set(pendentes_investimentos) | set(pendentes_banking))
    if pendentes:
        notify.send_alert(
            settings,
            subject=f"[Saldo Clientes] {len(pendentes)} banker(s) sem e-mail cadastrado",
            body=(
                f"Os banker_id(s) abaixo aparecem na planilha de saldo (responsável) mas não "
                f"têm e-mail cadastrado em bankers.csv — os clientes deles NÃO foram enviados "
                f"nesta execução:\n\n" + "\n".join(f"- {b}" for b in pendentes)
            ),
        )

    por_banker_investimentos = {g.banker_id: g for g in grupos_investimentos}
    por_banker_banking = {g.banker_id: g for g in grupos_banking}
    todos_banker_ids = sorted(set(por_banker_investimentos) | set(por_banker_banking))

    if not todos_banker_ids:
        logger.warning("Nenhum grupo de banker pronto para envio nesta execução.")
        return

    data_ref = date.today()
    assinatura = settings["assinatura"]
    assunto_template = settings.get("assunto_template", "Saldo em Conta - {data}")

    saida_teste = ROOT / "saida_teste"
    falhas = []

    for banker_id in todos_banker_ids:
        grupo_inv = por_banker_investimentos.get(banker_id)
        grupo_bank = por_banker_banking.get(banker_id)
        banker_nome = (grupo_inv or grupo_bank).banker_nome
        email = (grupo_inv or grupo_bank).email

        if grupo_inv:
            grupo_inv.clientes = grupo_inv.clientes.sort_values("saldo", ascending=False).reset_index(drop=True)
        if grupo_bank:
            grupo_bank.clientes = grupo_bank.clientes.sort_values("saldo", ascending=False).reset_index(drop=True)

        qtd_inv = len(grupo_inv.clientes) if grupo_inv else 0
        qtd_bank = len(grupo_bank.clientes) if grupo_bank else 0
        if log_sensivel:
            logger.info(
                "Banker %s (%s): %d conta(s) em Investimentos, %d em Banking.",
                banker_nome,
                email,
                qtd_inv,
                qtd_bank,
            )
        else:
            logger.info("Banker %s: %d conta(s) em Investimentos, %d em Banking.", banker_nome, qtd_inv, qtd_bank)

        subject = assunto_template.format(banker=banker_nome, data=data_ref.strftime("%d/%m/%Y"))

        imagem_inv = tabela_imagem.gerar_png(grupo_inv) if grupo_inv else None
        imagem_bank = tabela_imagem.gerar_png(grupo_bank) if grupo_bank else None
        cid_inv = f"saldo-investimentos-{banker_id}"
        cid_bank = f"saldo-banking-{banker_id}"

        if dry_run:
            data_uri_inv = (
                "data:image/png;base64," + base64.b64encode(imagem_inv).decode("ascii") if imagem_inv else None
            )
            data_uri_bank = (
                "data:image/png;base64," + base64.b64encode(imagem_bank).decode("ascii") if imagem_bank else None
            )
            html_body = email_builder.montar_corpo_html(banker_nome, assinatura, data_ref, data_uri_inv, data_uri_bank)
            saida_teste.mkdir(parents=True, exist_ok=True)
            destino = saida_teste / f"{banker_id}.html"
            destino.write_text(html_body, encoding="utf-8")
            logger.info("[DRY-RUN] E-mail de %s gravado em %s (nada foi enviado).", banker_nome, destino)
            continue

        imagens = [(imagem_inv, cid_inv)] if imagem_inv else []
        imagens += [(imagem_bank, cid_bank)] if imagem_bank else []

        try:
            notify.enviar_email_banker(
                settings["email"],
                grupo_inv or grupo_bank,
                subject,
                imagens,
                lambda aviso, img_i=imagem_inv, img_b=imagem_bank: email_builder.montar_corpo_html(
                    banker_nome,
                    assinatura,
                    data_ref,
                    f"cid:{cid_inv}" if img_i else None,
                    f"cid:{cid_bank}" if img_b else None,
                    aviso_teste=aviso,
                ),
            )
        except Exception as exc:
            logger.error("Falha ao enviar e-mail para banker %s: %s", banker_id, exc, exc_info=True)
            falhas.append(banker_id)

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
        history_log.append_snapshot(grupos_investimentos, "investimentos", data_ref, history_path)
        history_log.append_snapshot(grupos_banking, "banking", data_ref, history_path)


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
