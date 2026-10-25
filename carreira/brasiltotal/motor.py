"""O motor da carreira: partidas, tabelas, fases de liga e de mata-mata.

Tudo aqui é dado puro (dicts e listas) para a carreira inteira caber num JSON salvo. Uma
partida é {"id", "data", "comp", "fase", "casa", "fora", "gc", "gf", "pen"}: gols da casa e de
fora (None enquanto não jogada) e, num jogo que precisa de vencedor, o vencedor dos pênaltis.
"""
import math, random

# ---- força e simulação ----

def forca(clube):
    """a força de um clube: a média dos 11 melhores overalls, com um goleiro entre eles"""
    el = clube.get("elenco") or []
    gks = sorted((p["overall"] for p in el if p.get("pos") == "GK"), reverse=True)
    linha = sorted((p["overall"] for p in el if p.get("pos") != "GK"), reverse=True)
    onze = gks[:1] + linha[:10]
    return sum(onze) / len(onze) if onze else 60.0


def _poisson(rng, lam):
    l, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= l:
            return k
        k += 1


def simular(rng, f_casa, f_fora, neutro=False):
    """(gols da casa, gols de fora): Poisson em cima da diferença de força"""
    d = (f_casa - f_fora) * 0.065
    casa = 1.32 if not neutro else 1.18
    fora = 1.02 if not neutro else 1.18
    return _poisson(rng, casa * math.exp(d / 2)), _poisson(rng, fora * math.exp(-d / 2))


def penaltis(rng, f_a, f_b):
    """o vencedor (0 = a, 1 = b) de uma disputa de pênaltis: quase cara ou coroa"""
    return 0 if rng.random() < 0.5 + (f_a - f_b) * 0.01 else 1


# ---- tabelas ----

def tabela(clubes, partidas):
    """a classificação: pontos, vitórias, saldo, gols pró (o critério da CBF, sem confronto direto)"""
    t = {c: {"clube": c, "j": 0, "v": 0, "e": 0, "d": 0, "gp": 0, "gc": 0, "pts": 0} for c in clubes}
    for m in partidas:
        if m["gc"] is None:
            continue
        for lado, gp, gc in ((m["casa"], m["gc"], m["gf"]), (m["fora"], m["gf"], m["gc"])):
            if lado not in t:
                continue
            r = t[lado]
            r["j"] += 1; r["gp"] += gp; r["gc"] += gc
            if gp > gc:
                r["v"] += 1; r["pts"] += 3
            elif gp == gc:
                r["e"] += 1; r["pts"] += 1
            else:
                r["d"] += 1
    linhas = list(t.values())
    linhas.sort(key=lambda r: (-r["pts"], -r["v"], -(r["gp"] - r["gc"]), -r["gp"], r["clube"]))
    return linhas


def rodadas(clubes, turnos=2):
    """todos contra todos (método do círculo): uma lista de rodadas, cada uma de pares (casa, fora)"""
    cs = list(clubes)
    if len(cs) % 2:
        cs.append(None)
    n = len(cs)
    ida = []
    for r in range(n - 1):
        pares = []
        for i in range(n // 2):
            a, b = cs[i], cs[n - 1 - i]
            if a is not None and b is not None:
                pares.append((a, b) if (r + i) % 2 == 0 else (b, a))
        ida.append(pares)
        cs = [cs[0]] + [cs[-1]] + cs[1:-1]
    todas = list(ida)
    for t in range(1, turnos):
        todas += [[(b, a) if t % 2 else (a, b) for a, b in r] for r in ida]
    return todas


def vencedor_confronto(jogos, rng=None, fa=0, fb=0):
    """quem passa num confronto: jogos é a lista das partidas (1 ou 2) entre a e b, a o mandante
    do primeiro jogo. Soma de gols; empate vai aos pênaltis do último jogo ("pen": o vencedor),
    ou, com "vantagem" no primeiro jogo, passa quem a tem"""
    a, b = jogos[0]["casa"], jogos[0]["fora"]
    ga = gb = 0
    for m in jogos:
        if m["gc"] is None:
            return None
        if m["casa"] == a:
            ga += m["gc"]; gb += m["gf"]
        else:
            ga += m["gf"]; gb += m["gc"]
    if ga != gb:
        return a if ga > gb else b
    if jogos[0].get("vantagem"):
        return jogos[0]["vantagem"]
    return jogos[-1].get("pen")
