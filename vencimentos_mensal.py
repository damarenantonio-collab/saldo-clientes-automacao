"""Envia por e-mail os vencimentos de renda fixa do mês — um e-mail por
responsável (banker), a partir da planilha consolidada do escritório
(`Vencimentos_RF.xlsx`, aba "Export"), que já traz o responsável de
cada linha. Cada e-mail contém só os vencimentos dos clientes daquele
responsável.

Pensado pra rodar todo dia útil (o Agendador de Tarefas do Windows não
tem um gatilho nativo de "primeiro dia útil do mês"): o script mesmo
decide se hoje é esse dia e só envia nesse caso. Nos outros dias, sai
sem fazer nada e sem erro.

Uso:
    python vencimentos_mensal.py [--config config/settings.yaml]
    python vencimentos_mensal.py --dry-run
    python vencimentos_mensal.py --mes 10 --ano 2026   # simula outro mês (pra teste)
    python vencimentos_mensal.py --forcar               # ignora a checagem de dia útil
"""

import argparse
import base64
import logging
import sys
import traceback
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from src import agrupador, bankers, email_builder_vencimentos, notify, tabela_vencimentos_imagem, vencimentos
from src.dias_uteis import eh_primeiro_dia_util, primeiro_dia_util
from src.meses import nome_mes

ROOT = Path(__file__).resolve().parent


def setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "execucao_vencimentos.log", encoding="utf-8"),
        ],
    )
    return logging.getLogger(__name__)


def load_settings(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _montar_grupos(df_venc, mapa_bankers: dict, todos_banker_ids: set[str]):
    """Um grupo por responsável conhecido (aparece na planilha, em
    qualquer mês) — mesmo os que não têm vencimento nenhum no mês sendo
    processado ainda recebem um e-mail (avisando disso), em vez de
    ficar em silêncio. `pendentes` são responsáveis que aparecem na
    planilha mas não têm e-mail cadastrado em bankers.csv.
    """
    if df_venc.empty:
        grupos, pendentes = [], []
    else:
        grupos, pendentes = agrupador.agrupar_por_banker(df_venc, mapa_bankers)

    ja_incluidos = {g.banker_id for g in grupos} | set(pendentes)
    colunas_vazias = ["conta", "cliente", "produto", "vencimento", "valor_liquido", "banker_id"]

    for banker_id in sorted(todos_banker_ids - ja_incluidos):
        info = mapa_bankers.get(banker_id)
        if info and info.get("email"):
            grupos.append(
                agrupador.GrupoBanker(
                    banker_id=banker_id,
                    banker_nome=info["nome"],
                    email=info["email"],
                    clientes=pd.DataFrame(columns=colunas_vazias),
                )
            )
        else:
            pendentes.append(banker_id)

    return grupos, pendentes


def run(settings: dict, logger: logging.Logger, dry_run: bool, mes_ref: date) -> None:
    planilha_xlsx = (ROOT / settings["vencimentos_xlsx"]).resolve()
    bankers_csv = (ROOT / settings["bankers_csv"]).resolve()
    sheet_name = settings.get("vencimentos_sheet", vencimentos.SHEET_PADRAO)

    if not planilha_xlsx.exists():
        raise RuntimeError(
            f"{planilha_xlsx} não encontrado. Aponte vencimentos_xlsx em settings.yaml para "
            f"a planilha de vencimentos consolidada do escritório."
        )
    if not bankers_csv.exists():
        raise RuntimeError(
            f"{bankers_csv} não encontrado. Copie config/bankers.example.csv para "
            f"config/bankers.csv e preencha com seus bankers."
        )

    todos_banker_ids = vencimentos.bankers_conhecidos(planilha_xlsx, sheet_name=sheet_name)
    df_venc = vencimentos.load_vencimentos(planilha_xlsx, mes_ref, sheet_name=sheet_name)
    mapa_bankers = bankers.load_bankers(bankers_csv)
    log_sensivel = settings.get("log_dados_sensiveis", False)

    mes_ano = f"{nome_mes(mes_ref.month)}/{mes_ref.year}"
    logger.info("Carregado(s) %d vencimento(s) de renda fixa para %s.", len(df_venc), mes_ano)

    grupos, pendentes = _montar_grupos(df_venc, mapa_bankers, todos_banker_ids)

    if pendentes:
        notify.send_alert(
            settings,
            subject=f"[Vencimentos] {len(pendentes)} responsável(is) sem e-mail cadastrado",
            body=(
                f"Os banker_id(s) abaixo aparecem na planilha de vencimentos (responsável) mas "
                f"não têm e-mail cadastrado em bankers.csv — os vencimentos deles NÃO foram "
                f"enviados nesta execução:\n\n" + "\n".join(f"- {b}" for b in pendentes)
            ),
        )

    if not grupos:
        logger.warning("Nenhum grupo de banker pronto para envio nesta execução.")
        return

    assinatura = settings["assinatura"]
    assunto_template = settings.get("assunto_template_vencimentos", "Vencimentos do Mês - {mes_ano}")
    assunto_mes_ano = f"{nome_mes(mes_ref.month).capitalize()}/{mes_ref.year}"

    saida_teste = ROOT / "saida_teste"
    falhas = []

    for grupo in grupos:
        qtd = len(grupo.clientes)
        if log_sensivel:
            logger.info("Banker %s (%s): %d vencimento(s) em %s.", grupo.banker_nome, grupo.email, qtd, mes_ano)
        else:
            logger.info("Banker %s: %d vencimento(s) em %s.", grupo.banker_nome, qtd, mes_ano)

        subject = assunto_template.format(mes_ano=assunto_mes_ano)
        imagem_png = tabela_vencimentos_imagem.gerar_png(grupo) if qtd > 0 else None
        cid = f"vencimentos-{grupo.banker_id}"

        if dry_run:
            data_uri = None
            if imagem_png is not None:
                data_uri = "data:image/png;base64," + base64.b64encode(imagem_png).decode("ascii")
            html_body = email_builder_vencimentos.montar_corpo_html(grupo, assinatura, mes_ref, data_uri)
            saida_teste.mkdir(parents=True, exist_ok=True)
            destino = saida_teste / f"vencimentos-{grupo.banker_id}.html"
            destino.write_text(html_body, encoding="utf-8")
            logger.info("[DRY-RUN] E-mail de vencimentos de %s gravado em %s (nada foi enviado).", grupo.banker_nome, destino)
            continue

        imagens = [(imagem_png, cid)] if imagem_png is not None else []
        try:
            notify.enviar_email_banker(
                settings["email"],
                grupo,
                subject,
                imagens,
                lambda aviso, g=grupo, c=cid, img=imagem_png: email_builder_vencimentos.montar_corpo_html(
                    g, assinatura, mes_ref, (f"cid:{c}" if img is not None else None), aviso_teste=aviso
                ),
            )
        except Exception as exc:
            logger.error("Falha ao enviar e-mail de vencimentos para banker %s: %s", grupo.banker_id, exc, exc_info=True)
            falhas.append(grupo.banker_id)

    if falhas:
        notify.send_alert(
            settings,
            subject=f"[Vencimentos] Falha ao enviar e-mail para {len(falhas)} banker(s)",
            body=(
                f"Falha ao enviar o e-mail de vencimentos ({mes_ano}) para os banker_id(s) abaixo. "
                f"Veja logs/execucao_vencimentos.log para detalhes:\n\n" + "\n".join(f"- {b}" for b in falhas)
            ),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config/settings.yaml", help="Caminho do settings.yaml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não envia nenhum e-mail; grava o HTML de cada banker em saida_teste/ para conferência.",
    )
    parser.add_argument("--mes", type=int, default=None, help="Mês a simular (1-12). Padrão: mês atual.")
    parser.add_argument("--ano", type=int, default=None, help="Ano a simular. Padrão: ano atual.")
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Ignora a checagem de 'hoje é o primeiro dia útil do mês' e envia mesmo assim.",
    )
    args = parser.parse_args()

    config_path = (ROOT / args.config).resolve()
    if not config_path.exists():
        print(
            f"Arquivo de configuração não encontrado: {config_path}\n"
            f"Copie config/settings.example.yaml para settings.yaml e ajuste os valores."
        )
        sys.exit(1)

    hoje = date.today()
    mes_simulado = args.mes is not None or args.ano is not None
    mes_ref = date(args.ano or hoje.year, args.mes or hoje.month, 1)

    settings = load_settings(config_path)
    logger = setup_logging(ROOT / "logs")

    if not args.dry_run and not args.forcar and not mes_simulado and not eh_primeiro_dia_util(hoje):
        logger.info(
            "Hoje (%s) não é o primeiro dia útil do mês (seria %s) — nada enviado. "
            "Use --forcar para enviar mesmo assim.",
            hoje.isoformat(),
            primeiro_dia_util(hoje.year, hoje.month).isoformat(),
        )
        return

    try:
        run(settings, logger, dry_run=args.dry_run, mes_ref=mes_ref)
    except Exception:
        logger.error("Falha na execução:\n%s", traceback.format_exc())
        notify.send_alert(
            settings,
            subject="[Vencimentos] Falha na execução",
            body=f"A execução de hoje falhou com o erro:\n\n{traceback.format_exc()}",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
