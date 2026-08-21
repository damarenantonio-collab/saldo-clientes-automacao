"""Envia por e-mail o saldo em conta dos clientes do family office — um
e-mail por banker, contendo apenas os clientes daquele banker.

No primeiro dia útil do mês, o mesmo e-mail também inclui os
vencimentos de renda fixa do mês (veja src/email_builder_combinado.py)
— não sai um segundo e-mail separado, é uma seção a mais no mesmo.

Uso:
    python main.py [--config config/settings.yaml]
    python main.py --dry-run     # não envia nada; grava o HTML de cada
                                  # banker em saida_teste/ pra conferir
    python main.py --dry-run --incluir-vencimentos   # força a seção de
                                  # vencimentos mesmo fora do 1º dia útil
    python main.py --dry-run --mes 10 --ano 2026      # idem, simulando
                                  # os vencimentos de outro mês
"""

import argparse
import base64
import logging
import sys
import traceback
from datetime import date
from pathlib import Path

import yaml

from src import (
    agrupador,
    bankers,
    email_builder,
    email_builder_combinado,
    history_log,
    notify,
    saldos,
    tabela_imagem,
    tabela_vencimentos_imagem,
    vencimentos,
)
from src.dias_uteis import eh_primeiro_dia_util
from src.meses import nome_mes

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


def _carregar_vencimentos_por_banker(settings, logger, saldos_xlsx: Path, banker_padrao: str, mapa_bankers: dict, mes_ref: date):
    sheet_name = settings.get("vencimentos_sheet", vencimentos.SHEET_PADRAO)
    df_venc = vencimentos.load_vencimentos(saldos_xlsx, banker_padrao, mes_ref, sheet_name=sheet_name)

    mes_ano = f"{nome_mes(mes_ref.month)}/{mes_ref.year}"
    logger.info("Também incluindo vencimentos de renda fixa: %d encontrado(s) para %s.", len(df_venc), mes_ano)

    if df_venc.empty:
        grupos_venc = [
            agrupador.GrupoBanker(banker_id=bid, banker_nome=info["nome"], email=info["email"], clientes=df_venc)
            for bid, info in mapa_bankers.items()
            if info.get("email")
        ]
        pendentes_venc = []
    else:
        grupos_venc, pendentes_venc = agrupador.agrupar_por_banker(df_venc, mapa_bankers)

    if pendentes_venc:
        notify.send_alert(
            settings,
            subject=f"[Saldo Clientes] {len(pendentes_venc)} banker(s) sem e-mail cadastrado (vencimentos)",
            body=(
                f"Os banker_id(s) abaixo aparecem nos vencimentos de {mes_ano} mas não têm "
                f"e-mail cadastrado em bankers.csv — os vencimentos deles NÃO foram incluídos "
                f"nesta execução:\n\n" + "\n".join(f"- {b}" for b in pendentes_venc)
            ),
        )

    return {g.banker_id: g for g in grupos_venc}


def run(settings: dict, logger: logging.Logger, dry_run: bool, incluir_vencimentos: bool, mes_ref: date) -> None:
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

    grupos_venc_por_banker = {}
    if incluir_vencimentos:
        grupos_venc_por_banker = _carregar_vencimentos_por_banker(
            settings, logger, saldos_xlsx, banker_padrao, mapa_bankers, mes_ref
        )

    data_ref = date.today()
    assinatura = settings["assinatura"]
    assunto_template = settings.get("assunto_template", "Saldo em Conta - {data}")
    assunto_template_combinado = settings.get(
        "assunto_template_combinado", "Saldo em Conta e Vencimentos do Mês - {data}"
    )

    saida_teste = ROOT / "saida_teste"
    falhas = []

    for grupo in grupos:
        qtd = len(grupo.clientes)
        total = grupo.clientes["saldo"].sum()

        grupo_venc = grupos_venc_por_banker.get(grupo.banker_id) if incluir_vencimentos else None
        qtd_venc = len(grupo_venc.clientes) if grupo_venc is not None else 0

        if log_sensivel and incluir_vencimentos:
            logger.info(
                "Banker %s (%s): %d cliente(s), total R$ %.2f; %d vencimento(s).",
                grupo.banker_nome, grupo.email, qtd, total, qtd_venc,
            )
        elif log_sensivel:
            logger.info("Banker %s (%s): %d cliente(s), total R$ %.2f.", grupo.banker_nome, grupo.email, qtd, total)
        elif incluir_vencimentos:
            logger.info("Banker %s: %d cliente(s), %d vencimento(s).", grupo.banker_nome, qtd, qtd_venc)
        else:
            logger.info("Banker %s: %d cliente(s).", grupo.banker_nome, qtd)

        imagem_saldo_png = tabela_imagem.gerar_png(grupo)
        cid_saldo = f"saldo-{grupo.banker_id}"

        imagem_venc_png = None
        cid_venc = f"vencimentos-{grupo.banker_id}"
        if grupo_venc is not None and qtd_venc > 0:
            imagem_venc_png = tabela_vencimentos_imagem.gerar_png(grupo_venc)

        if incluir_vencimentos:
            subject = assunto_template_combinado.format(data=data_ref.strftime("%d/%m/%Y"))
        else:
            subject = assunto_template.format(banker=grupo.banker_nome, data=data_ref.strftime("%d/%m/%Y"))

        if dry_run:
            saldo_src = "data:image/png;base64," + base64.b64encode(imagem_saldo_png).decode("ascii")
            if incluir_vencimentos:
                venc_src = None
                if imagem_venc_png is not None:
                    venc_src = "data:image/png;base64," + base64.b64encode(imagem_venc_png).decode("ascii")
                html_body = email_builder_combinado.montar_corpo_html(grupo, mes_ref, assinatura, saldo_src, venc_src)
            else:
                html_body = email_builder.montar_corpo_html(grupo, assinatura, data_ref, saldo_src)

            saida_teste.mkdir(parents=True, exist_ok=True)
            destino = saida_teste / f"{grupo.banker_id}.html"
            destino.write_text(html_body, encoding="utf-8")
            logger.info("[DRY-RUN] E-mail de %s gravado em %s (nada foi enviado).", grupo.banker_nome, destino)
            continue

        imagens = [(imagem_saldo_png, cid_saldo)]
        if imagem_venc_png is not None:
            imagens.append((imagem_venc_png, cid_venc))

        try:
            if incluir_vencimentos:
                notify.enviar_email_banker(
                    settings["email"],
                    grupo,
                    subject,
                    imagens,
                    lambda aviso, g=grupo, cs=cid_saldo, cv=cid_venc, imgv=imagem_venc_png: email_builder_combinado.montar_corpo_html(
                        g,
                        mes_ref,
                        assinatura,
                        f"cid:{cs}",
                        (f"cid:{cv}" if imgv is not None else None),
                        aviso_teste=aviso,
                    ),
                )
            else:
                notify.enviar_email_banker(
                    settings["email"],
                    grupo,
                    subject,
                    imagens,
                    lambda aviso, g=grupo, c=cid_saldo: email_builder.montar_corpo_html(
                        g, assinatura, data_ref, f"cid:{c}", aviso_teste=aviso
                    ),
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
    parser.add_argument(
        "--incluir-vencimentos",
        action="store_true",
        help="Força incluir a seção de vencimentos do mês atual, mesmo fora do primeiro dia útil (pra testar sem esperar o dia certo).",
    )
    parser.add_argument(
        "--mes", type=int, default=None, help="Mês dos vencimentos a incluir (1-12) — implica --incluir-vencimentos. Padrão: mês atual."
    )
    parser.add_argument("--ano", type=int, default=None, help="Ano dos vencimentos a incluir. Padrão: ano atual.")
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
    incluir_vencimentos = mes_simulado or args.incluir_vencimentos or eh_primeiro_dia_util(hoje)

    settings = load_settings(config_path)
    logger = setup_logging(ROOT / "logs")

    try:
        run(settings, logger, dry_run=args.dry_run, incluir_vencimentos=incluir_vencimentos, mes_ref=mes_ref)
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
