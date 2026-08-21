"""Cálculo de "primeiro dia útil do mês" — usado por main.py pra decidir
se inclui a seção de vencimentos no e-mail de hoje, e por
vencimentos_mensal.py (ferramenta manual de teste/preview).
"""

from datetime import date, timedelta


def primeiro_dia_util(ano: int, mes: int) -> date:
    dia = date(ano, mes, 1)
    while dia.weekday() >= 5:  # 5=sábado, 6=domingo
        dia += timedelta(days=1)
    return dia


def eh_primeiro_dia_util(hoje: date) -> bool:
    """Não considera feriados — só fins de semana. Se um feriado cair no
    que seria o primeiro dia útil, o e-mail sai nesse feriado mesmo."""
    return hoje == primeiro_dia_util(hoje.year, hoje.month)
