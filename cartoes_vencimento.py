"""Avisa o banker quando a fatura de cartão de crédito de um cliente
está prestes a vencer, a partir de uma planilha de controle mantida
manualmente (não vem do BTG).

Só envia e-mail quando há algum vencimento dentro da janela de aviso
(`cartoes_dias_aviso` em settings.yaml, padrão 1 dia) — em vez de
mandar todo dia mesmo sem nada a avisar.

Pensado pra rodar diariamente via Agendador de Tarefas. Veja o README,
seção do boletim de cartões, sobre a limitação de rodar só em dias
úteis (um vencimento de fim de semana pode não ter aviso a tempo).

Uso:
    python cartoes_vencimento.py [--config config/settings.yaml]
    python cartoes_vencimento.py --dry-run
    python cartoes_vencimento.py --dry-run --data 2026-09-14   # simula outra data
"""

import argparse
import base64
import logging
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

import yaml

from src import bankers, cartoes, email_builder_cartoes, notify, tabela_cartoes_imagem
from src.agrupador import GrupoBanker

ROOT = Path(__file__).resolve().parent


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "execucao_cartoes.log", encoding="utf-8"),
        ],
    )
    return logging.getLogger(__name__)


def load_settings(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(settings: dict, logger: logging.Logger, dry_run: bool, hoje: date) -> None:
    cartoes_xlsx = (ROOT / settings["cartoes_xlsx"]).resolve()
    bankers_csv = (ROOT / settings["bankers_csv"]).resolve()
    sheet_name = settings.get("cartoes_sheet", cartoes.SHEET_PADRAO)
    dias_aviso = settings.get("cartoes_dias_aviso", 1)
    banker_id = settings["cartoes_banker_id"]

    if not cartoes_xlsx.exists():
        raise RuntimeError(
            f"{cartoes_xlsx} não encontrado. Aponte cartoes_xlsx em settings.yaml para "
            f"a planilha de controle de vencimento de cartões."
        )
    if not bankers_csv.exists():
        raise RuntimeError(
            f"{bankers_csv} não encontrado. Copie config/bankers.example.csv para "
            f"config/bankers.csv e preencha com seus bankers."
        )

    df = cartoes.load_cartoes(cartoes_xlsx, sheet_name=sheet_name, hoje=hoje)
    mapa_bankers = bankers.load_bankers(bankers_csv)
    log_sensivel = settings.get("log_dados_sensiveis", False)

    logger.info("Carregado(s) %d cartão(ões) ativo(s) da aba '%s'.", len(df), sheet_name)

    df_aviso = df[df["dias_ate_vencer"] <= dias_aviso].sort_values("dias_ate_vencer").reset_index(drop=True)

    if df_aviso.empty:
        logger.info("Nenhum vencimento de cartão dentro da janela de %d dia(s). Nada enviado.", dias_aviso)
        return

    info = mapa_bankers.get(banker_id)
    if not info or not info.get("email"):
        notify.send_alert(
            settings,
            subject=f"[Cartões] banker '{banker_id}' sem e-mail cadastrado",
            body=(
                f"O banker_id configurado em cartoes_banker_id ('{banker_id}') não está em "
                f"bankers.csv ou não tem e-mail cadastrado — os avisos de cartão de "
                f"{len(df_aviso)} cliente(s) NÃO foram enviados nesta execução."
            ),
        )
        return

    grupo = GrupoBanker(banker_id=banker_id, banker_nome=info["nome"], email=info["email"], clientes=df_aviso)

    if log_sensivel:
        logger.info("Banker %s (%s): %d aviso(s) de cartão.", grupo.banker_nome, grupo.email, len(df_aviso))
    else:
        logger.info("Banker %s: %d aviso(s) de cartão.", grupo.banker_nome, len(df_aviso))

    assinatura = settings["assinatura"]
    assunto_template = settings.get("assunto_template_cartoes", "Vencimento de Fatura de Cartão - {data}")
    subject = assunto_template.format(data=hoje.strftime("%d/%m/%Y"))

    imagem_png = tabela_cartoes_imagem.gerar_png(grupo)
    cid = f"cartoes-{grupo.banker_id}"

    saida_teste = ROOT / "saida_teste"

    if dry_run:
        data_uri = "data:image/png;base64," + base64.b64encode(imagem_png).decode("ascii")
        html_body = email_builder_cartoes.montar_corpo_html(grupo, assinatura, data_uri)
        saida_teste.mkdir(parents=True, exist_ok=True)
        destino = saida_teste / f"cartoes-{grupo.banker_id}.html"
        destino.write_text(html_body, encoding="utf-8")
        logger.info("[DRY-RUN] E-mail de cartões de %s gravado em %s (nada foi enviado).", grupo.banker_nome, destino)
        return

    try:
        notify.enviar_email_banker(
            settings["email"],
            grupo,
            subject,
            [(imagem_png, cid)],
            lambda aviso, g=grupo, c=cid: email_builder_cartoes.montar_corpo_html(
                g, assinatura, f"cid:{c}", aviso_teste=aviso
            ),
        )
    except Exception as exc:
        logger.error("Falha ao enviar e-mail de cartões para banker %s: %s", grupo.banker_id, exc, exc_info=True)
        notify.send_alert(
            settings,
            subject="[Cartões] Falha ao enviar e-mail",
            body=(
                f"Falha ao enviar o e-mail de aviso de cartões para o banker {grupo.banker_id}. "
                f"Veja logs/execucao_cartoes.log para detalhes:\n\n{exc}"
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config/settings.yaml", help="Caminho do settings.yaml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não envia nenhum e-mail; grava o HTML em saida_teste/ para conferência.",
    )
    parser.add_argument(
        "--data", default=None, help="Data a simular (AAAA-MM-DD). Padrão: hoje. Útil pra testar com --dry-run."
    )
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve()
    if not config_path.exists():
        print(
            f"Arquivo de configuração não encontrado: {config_path}\n"
            f"Copie config/settings.example.yaml para settings.yaml e ajuste os valores."
        )
        sys.exit(1)

    hoje = datetime.strptime(args.data, "%Y-%m-%d").date() if args.data else date.today()

    settings = load_settings(config_path)
    logger = setup_logging(ROOT / "logs")

    try:
        run(settings, logger, dry_run=args.dry_run, hoje=hoje)
    except Exception:
        logger.error("Falha na execução:\n%s", traceback.format_exc())
        notify.send_alert(
            settings,
            subject="[Cartões] Falha na execução",
            body=f"A execução de hoje falhou com o erro:\n\n{traceback.format_exc()}",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
