"""As datas de cada temporada.

As Séries jogam no fim de semana (cada clube está em uma só, então não se cruzam) e as copas
na quarta-feira. As datas vêm da temporada de 2026 e, nos anos seguintes, caem no mesmo dia da
semana mais próximo da mesma data.
"""
import datetime

D = datetime.date


def _ajusta(ano, mes, dia, semana):
    """a data do ano `ano` no dia da semana `semana` (0 = segunda) mais próximo de mes/dia"""
    base = D(ano, mes, dia)
    delta = (semana - base.weekday() + 7) % 7
    if delta > 3:
        delta -= 7
    return base + datetime.timedelta(days=delta)


def semanal(ano, mes, dia, semana, n, passo=7):
    """n datas, uma por semana, a partir do dia da semana mais próximo de mes/dia"""
    d0 = _ajusta(ano, mes, dia, semana)
    return [(d0 + datetime.timedelta(days=passo * k)).isoformat() for k in range(n)]


def quarta(ano, mes, dia):
    return _ajusta(ano, mes, dia, 2).isoformat()


def domingo(ano, mes, dia):
    return _ajusta(ano, mes, dia, 6).isoformat()


def datas(ano):
    """as datas de cada fase de cada competição da temporada `ano`"""
    q = lambda m, d: quarta(ano, m, d)
    return {
        "serie-a": {"liga": semanal(ano, 3, 15, 6, 38)},                       # domingos, março a novembro
        "serie-b": {"liga": semanal(ano, 3, 14, 5, 38)},                       # sábados
        "serie-c": {"primeira": semanal(ano, 4, 4, 5, 19),                     # sábados, abril a agosto
                    "segunda": semanal(ano, 8, 22, 5, 6),
                    "final": semanal(ano, 10, 3, 5, 2)},
        "serie-d": {"grupos": semanal(ano, 4, 12, 6, 10),                      # domingos, abril a junho
                    "oitavas": semanal(ano, 6, 21, 6, 2),
                    "quartas": semanal(ano, 7, 5, 6, 2),
                    "semifinal": semanal(ano, 7, 19, 6, 2),
                    "final": semanal(ano, 8, 2, 6, 2)},
        "copa-do-brasil": {"fase1": [q(2, 25)], "fase2": [q(3, 11)], "fase3": [q(4, 15)], "fase4": [q(4, 29)],
                           "oitavas": [q(7, 29), q(8, 5)], "quartas": [q(8, 26), q(9, 16)],
                           "semifinal": [q(10, 14), q(10, 21)], "final": [domingo(ano, 12, 6)]},
    }
