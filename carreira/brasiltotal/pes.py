"""A ponte com o PES: o módulo brasiltotal.lua, que roda dentro do jogo pelo Sider, lê o seu
próximo jogo de partida.txt e grava o placar ao vivo em placar.txt, os dois na pasta de dados
da carreira (%APPDATA%\\BrasilTotal)."""
import os


def escrever_partida(pasta, m, nome, texto, decide):
    """o jogo que o PES deve mostrar no overlay e conferir: m é a partida pendente"""
    linhas = ["id=%s" % m["id"], "casa=%d" % m["casa"], "fora=%d" % m["fora"],
              "nome_casa=%s" % nome(m["casa"]), "nome_fora=%s" % nome(m["fora"]),
              "texto=%s" % texto, "decide=%d" % (1 if decide else 0)]
    with open(os.path.join(pasta, "partida.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    # o placar antigo não vale para o jogo novo
    apagar_placar(pasta)


def apagar_partida(pasta):
    for n in ("partida.txt", "placar.txt"):
        try:
            os.remove(os.path.join(pasta, n))
        except OSError:
            pass


def apagar_placar(pasta):
    try:
        os.remove(os.path.join(pasta, "placar.txt"))
    except OSError:
        pass


def ler_placar(pasta, m):
    """o placar que o PES gravou para a partida m, como (gols da casa, gols de fora, minuto,
    terminou), já do ponto de vista de m mesmo que os lados tenham sido trocados no Amistoso.
    None se não há placar deste jogo"""
    try:
        with open(os.path.join(pasta, "placar.txt"), encoding="utf-8") as f:
            t = dict(l.rstrip("\n").split("=", 1) for l in f if "=" in l)
        casa, fora, gc, gf = int(t["casa"]), int(t["fora"]), int(t["gc"]), int(t["gf"])
    except (OSError, KeyError, ValueError):
        return None
    if t.get("id") not in (None, "", str(m["id"])):
        return None
    minuto = t.get("minuto", "")
    terminou = t.get("fim") == "1"
    if (casa, fora) == (m["casa"], m["fora"]):
        return gc, gf, minuto, terminou
    if (casa, fora) == (m["fora"], m["casa"]):
        return gf, gc, minuto, terminou
    return None
