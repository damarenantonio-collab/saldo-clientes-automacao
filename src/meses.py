"""Nomes de mês em português — fixo (não depende do locale configurado
no Windows onde a automação roda, que é bem inconsistente entre máquinas).
"""

MESES_PT = [
    "",
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]


def nome_mes(mes: int) -> str:
    return MESES_PT[mes]
