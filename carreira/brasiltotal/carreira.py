"""Uma carreira: a temporada, as competições e o dia a dia até o próximo jogo do seu clube.

O estado inteiro é um dict que vira JSON (salvar/carregar). As competições são o formato real
de 2026 adaptado aos 84 clubes do mundo (Séries A 20, B 20, C 20, D 24), com 4 que sobem e 4 que
descem entre todas as séries (decisão da Bia), e a Copa do Brasil com todos eles.
"""
import datetime, json, random

from . import calendario, motor

NOMES = {"serie-a": "Brasileirão Série A", "serie-b": "Brasileirão Série B",
         "serie-c": "Brasileirão Série C", "serie-d": "Brasileirão Série D",
         "copa-do-brasil": "Copa do Brasil"}
SERIES = ("A", "B", "C", "D")
SOBEM = 4


class Carreira:
    def __init__(self, estado, mundo):
        self.e = estado
        self.clubes = {c["id"]: c for c in mundo["clubes"]}
        self._forca = {}
        self.rng = random.Random(estado.get("semente", 0) * 1000003 + estado.get("passos", 0))

    # ---- criar, salvar, carregar ----

    @classmethod
    def nova(cls, mundo, clube, ano=2026, semente=None):
        series = {s: [c["id"] for c in mundo["clubes"] if c["serie"] == s] for s in SERIES}
        if not any(clube in v for v in series.values()):
            raise ValueError("o clube %r não está em nenhuma série" % clube)
        e = {"versao": 1, "ano": ano, "clube": clube, "semente": semente if semente is not None else random.randrange(1 << 30),
             "passos": 0, "series": series, "partidas": {}, "seq": 0, "comps": {}, "noticias": [],
             "historico": []}
        c = cls(e, mundo)
        # a primeira temporada não tem tabela anterior: cada série vai pela força dos elencos
        for s in SERIES:
            series[s].sort(key=lambda t: -c.forca(t))
        c._temporada()
        return c

    def salvar(self, caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(self.e, f, ensure_ascii=False)

    @classmethod
    def carregar(cls, caminho, mundo):
        with open(caminho, encoding="utf-8") as f:
            return cls(json.load(f), mundo)

    # ---- consultas ----

    def nome(self, t):
        return self.clubes[t]["nome"] if t in self.clubes else str(t)

    def forca(self, t):
        if t not in self._forca:
            self._forca[t] = motor.forca(self.clubes.get(t, {}))
        return self._forca[t]

    def serie_de(self, t):
        return next((s for s, v in self.e["series"].items() if t in v), None)

    def partida(self, pid):
        return self.e["partidas"][str(pid)]

    def partidas_de(self, t=None):
        t = self.e["clube"] if t is None else t
        return sorted((m for m in self.e["partidas"].values() if t in (m["casa"], m["fora"])), key=lambda m: m["data"])

    def proximo_jogo(self):
        """a próxima partida do seu clube ainda não jogada"""
        return next((m for m in self.partidas_de() if m["gc"] is None), None)

    def tabela(self, cid, fase=0, grupo=0):
        f = self.e["comps"][cid]["fases"][fase]
        ms = [self.partida(p) for p in f["partidas"]]
        return motor.tabela(f["grupos"][grupo], ms)

    def noticia(self, texto):
        self.e["noticias"].insert(0, {"data": self.e["data"], "texto": texto})
        del self.e["noticias"][200:]

    # ---- a temporada ----

    def _temporada(self):
        """monta as competições do ano e o ranking que a Copa do Brasil usa"""
        e = self.e
        ano = e["ano"]
        e["data"] = "%d-01-01" % ano
        e["partidas"] = {}
        e["ranking"] = [t for s in SERIES for t in e["series"][s]]
        dt = calendario.datas(ano)
        s = e["series"]
        e["comps"] = {
            "serie-a": self._comp("serie-a", [self._liga("Pontos corridos", [s["A"]], 2, dt["serie-a"]["liga"])]),
            "serie-b": self._comp("serie-b", [self._liga("Pontos corridos", [s["B"]], 2, dt["serie-b"]["liga"])]),
            "serie-c": self._comp("serie-c", [self._liga("Primeira fase", [s["C"]], 1, dt["serie-c"]["primeira"])]),
            "serie-d": self._comp("serie-d", [self._liga("Primeira fase", self._grupos(s["D"], 4), 2, dt["serie-d"]["grupos"])]),
            "copa-do-brasil": self._comp("copa-do-brasil", [self._copa_fase1(dt)]),
        }
        self.noticia("Começa a temporada %d." % ano)

    def _comp(self, cid, fases):
        return {"nome": NOMES[cid], "fases": fases, "campeao": None}

    def _grupos(self, clubes, n):
        """n grupos pelo ranking em serpentina (cabeças de chave espalhados)"""
        g = [[] for _ in range(n)]
        for i, t in enumerate(clubes):
            k = i % (2 * n)
            g[k if k < n else 2 * n - 1 - k].append(t)
        return g

    def _nova_partida(self, comp, fase, data, casa, fora, **extra):
        e = self.e
        e["seq"] += 1
        m = {"id": e["seq"], "data": data, "comp": comp, "fase": fase, "casa": casa, "fora": fora,
             "gc": None, "gf": None, "pen": None}
        m.update(extra)
        e["partidas"][str(m["id"])] = m
        return m["id"]

    def _liga(self, nome, grupos, turnos, datas):
        return {"nome": nome, "tipo": "liga", "grupos": grupos, "turnos": turnos, "datas": datas, "partidas": None}

    def _mata(self, nome, pares, datas, vantagem=False, neutro=False):
        """pares: [(mandante do primeiro jogo, o outro)]"""
        return {"nome": nome, "tipo": "mata", "pares": [list(p) for p in pares], "datas": datas,
                "vantagem": vantagem, "neutro": neutro, "partidas": None, "confrontos": None}

    def _abrir(self, cid, k):
        """cria as partidas da fase k da competição cid"""
        f = self.e["comps"][cid]["fases"][k]
        ps = []
        if f["tipo"] == "liga":
            for g in f["grupos"]:
                for r, jogos in enumerate(motor.rodadas(g, f["turnos"])):
                    for a, b in jogos:
                        ps.append(self._nova_partida(cid, k, f["datas"][r], a, b, rodada=r + 1))
        else:
            f["confrontos"] = []
            for a, b in f["pares"]:
                ids = []
                for j, d in enumerate(f["datas"]):
                    casa, fora = (a, b) if j % 2 == 0 else (b, a)
                    ultimo = j == len(f["datas"]) - 1
                    extra = {"decide": ultimo}
                    if f["vantagem"] and j == 0:
                        # jogo único com vantagem do empate para o mais bem ranqueado (o visitante)
                        extra["vantagem"] = min((a, b), key=self._rank)
                    if f["neutro"]:
                        extra["neutro"] = True
                    ids.append(self._nova_partida(cid, k, d, casa, fora, **extra))
                f["confrontos"].append(ids)
                ps += ids
        f["partidas"] = ps

    def _rank(self, t):
        r = self.e["ranking"]
        return r.index(t) if t in r else len(r)

    # ---- os jogos ----

    def precisa_penaltis(self, m):
        """se, com o placar desta partida, o confronto termina empatado e vai aos pênaltis"""
        if not m.get("decide"):
            return False
        f = self.e["comps"][m["comp"]]["fases"][m["fase"]]
        conf = next(c for c in f["confrontos"] if m["id"] in c)
        jogos = [self.partida(p) for p in conf]
        if any(j["gc"] is None for j in jogos):
            return False
        a, b = jogos[0]["casa"], jogos[0]["fora"]
        ga = sum(j["gc"] if j["casa"] == a else j["gf"] for j in jogos)
        gb = sum(j["gf"] if j["casa"] == a else j["gc"] for j in jogos)
        return ga == gb and not jogos[0].get("vantagem")

    def registrar(self, pid, gc, gf, pen=None):
        """o placar de uma partida (o seu, vindo do PES, ou um simulado); pen: o clube que venceu
        nos pênaltis, quando o confronto termina empatado"""
        m = self.partida(pid)
        m["gc"], m["gf"] = int(gc), int(gf)
        if self.precisa_penaltis(m):
            if pen not in (m["casa"], m["fora"]):
                m["gc"] = m["gf"] = None
                raise ValueError("o confronto terminou empatado: diga quem venceu nos pênaltis")
            m["pen"] = pen
        self.e["passos"] += 1
        self._fechar_fases()

    def simular_meu(self, pid):
        """o seu jogo decidido pelo simulador, sem passar pelo PES"""
        self._simular(self.partida(pid))
        self.e["passos"] += 1
        self._fechar_fases()

    def _simular(self, m):
        fc, ff = self.forca(m["casa"]), self.forca(m["fora"])
        gc, gf = motor.simular(self.rng, fc, ff, m.get("neutro"))
        m["gc"], m["gf"] = gc, gf
        if self.precisa_penaltis(m):
            m["pen"] = (m["casa"], m["fora"])[motor.penaltis(self.rng, fc, ff)]

    def avancar(self, ate_meu_jogo=True):
        """joga os dias até o próximo jogo do seu clube (que fica para você) ou o fim da
        temporada. Devolve a sua partida pendente, ou None quando a temporada acabou"""
        while True:
            pend = sorted((m for m in self.e["partidas"].values() if m["gc"] is None), key=lambda m: (m["data"], m["id"]))
            if not pend:
                if self._fechar_fases():
                    continue
                self._fim_de_temporada()
                return None
            dia = pend[0]["data"]
            self.e["data"] = dia
            meu = None
            for m in pend:
                if m["data"] != dia:
                    break
                if self.e["clube"] in (m["casa"], m["fora"]):
                    meu = m
                    continue
                self._simular(m)
            self.e["passos"] += 1
            self._fechar_fases()
            if meu is not None and ate_meu_jogo:
                return meu
            if meu is not None:
                self._simular(meu)
                self._fechar_fases()

    def _fechar_fases(self):
        """abre as fases que estão prontas e fecha as que terminaram; True se mudou algo"""
        mudou = False
        for cid, c in self.e["comps"].items():
            if c["campeao"] is not None:
                continue
            k = len(c["fases"]) - 1
            f = c["fases"][k]
            if f["partidas"] is None:
                self._abrir(cid, k)
                mudou = True
                continue
            if all(self.partida(p)["gc"] is not None for p in f["partidas"]):
                self._noticia_confronto(c, f)
                prox = getattr(self, "_depois_" + cid.replace("-", "_"))(c, k)
                if prox is None:
                    mudou = True
                elif prox:
                    c["fases"].append(prox)
                    mudou = True
        return mudou

    def _noticia_confronto(self, c, f):
        """a notícia do confronto do seu clube num mata-mata que acabou de terminar"""
        meu = self.e["clube"]
        for conf in f.get("confrontos") or []:
            jogos = [self.partida(p) for p in conf]
            if meu not in (jogos[0]["casa"], jogos[0]["fora"]):
                continue
            w = motor.vencedor_confronto(jogos)
            outro = jogos[0]["fora"] if jogos[0]["casa"] == meu else jogos[0]["casa"]
            como = ""
            if jogos[-1].get("pen"):
                como = " nos pênaltis"
            elif jogos[0].get("vantagem") and jogos[0]["gc"] == jogos[0]["gf"]:
                como = " com a vantagem do empate"
            if w == meu:
                self.noticia("%s: você passou por %s%s." % (c["nome"] + ", " + f["nome"], self.nome(outro), como))
            else:
                self.noticia("%s: você foi eliminado por %s%s." % (c["nome"] + ", " + f["nome"], self.nome(outro), como))

    def vencedores(self, f):
        ws = []
        for conf in f["confrontos"]:
            ws.append(motor.vencedor_confronto([self.partida(p) for p in conf]))
        return ws

    def _classificacao(self, f, g=0):
        return [r["clube"] for r in motor.tabela(f["grupos"][g], [self.partida(p) for p in f["partidas"]])]

    def _campeao(self, c, t, texto=None):
        c["campeao"] = t
        artigo = "da" if c["nome"].startswith("Copa") else "do"
        self.noticia(texto or "%s é campeão %s %s!" % (self.nome(t), artigo, c["nome"]))
        return None

    # ---- formatos ----

    def _depois_serie_a(self, c, k):
        c["final"] = self._classificacao(c["fases"][0])
        return self._campeao(c, c["final"][0])

    def _depois_serie_b(self, c, k):
        c["final"] = self._classificacao(c["fases"][0])
        return self._campeao(c, c["final"][0])

    def _depois_serie_c(self, c, k):
        dt = calendario.datas(self.e["ano"])["serie-c"]
        f = c["fases"][k]
        if k == 0:
            # os 8 primeiros fazem dois grupos de 4 em turno e returno; os 4 últimos caem
            cl = self._classificacao(f)
            c["primeira"] = cl
            g1, g2 = [cl[0], cl[3], cl[4], cl[7]], [cl[1], cl[2], cl[5], cl[6]]
            return self._liga("Segunda fase", [g1, g2], 2, dt["segunda"])
        if k == 1:
            g1, g2 = self._classificacao(f, 0), self._classificacao(f, 1)
            c["sobem"] = g1[:2] + g2[:2]
            self.noticia("Série C: sobem %s." % ", ".join(self.nome(t) for t in c["sobem"]))
            return self._mata("Final", [(g2[0], g1[0])], dt["final"])
        return self._campeao(c, self.vencedores(f)[0])

    def _depois_serie_d(self, c, k):
        dt = calendario.datas(self.e["ano"])["serie-d"]
        f = c["fases"][k]
        if k == 0:
            # os 4 primeiros de cada grupo: oitavas, 1º de um grupo contra o 4º de outro
            g = [self._classificacao(f, i) for i in range(4)]
            pares = []
            for i in range(4):
                o = g[(i + 1) % 4]
                pares += [(o[3], g[i][0]), (o[2], g[i][1])]
            return self._mata("Oitavas", pares, dt["oitavas"])
        ws = self.vencedores(f)
        if f["nome"] == "Oitavas":
            return self._mata("Quartas", self._sorteio(ws), dt["quartas"])
        if f["nome"] == "Quartas":
            c["sobem"] = list(ws)
            self.noticia("Série D: sobem %s." % ", ".join(self.nome(t) for t in ws))
            return self._mata("Semifinal", self._sorteio(ws), dt["semifinal"])
        if f["nome"] == "Semifinal":
            return self._mata("Final", self._sorteio(ws), dt["final"])
        return self._campeao(c, ws[0])

    def _sorteio(self, clubes, potes=False):
        """pares sorteados; com potes, cada mais bem ranqueado pega um do pote de baixo, e o de
        baixo manda o primeiro jogo"""
        cs = list(clubes)
        if potes:
            cs.sort(key=self._rank)
            n = len(cs) // 2
            cima, baixo = cs[:n], cs[n:]
            self.rng.shuffle(baixo)
            return [(baixo[i], cima[i]) for i in range(n)]
        self.rng.shuffle(cs)
        return [(cs[i], cs[i + 1]) for i in range(0, len(cs) - 1, 2)]

    def _pareados(self, clubes):
        """jogo único da CBF nas primeiras fases: o 1º do ranking contra o último, e assim por
        diante; o mais bem ranqueado joga fora e tem a vantagem do empate"""
        cs = sorted(clubes, key=self._rank)
        n = len(cs)
        return [(cs[n - 1 - i], cs[i]) for i in range(n // 2)]

    def _copa_fase1(self, dt):
        s = self.e["series"]
        return self._mata("1ª fase", self._pareados(s["C"] + s["D"]), dt["copa-do-brasil"]["fase1"], vantagem=True)

    def _depois_copa_do_brasil(self, c, k):
        """1ª fase: Séries C e D (44). 2ª: os 22 vencedores e a B do 3º ao 20º. 3ª: os 20, o 1º e
        o 2º da B e a A do 11º ao 20º. 4ª: os 16 e a A do 7º ao 10º. Oitavas: os 10 e os 6
        primeiros da A (a Libertadores). As duas primeiras fases em jogo único com vantagem do
        empate, a 3ª e a 4ª em jogo único com pênaltis, depois ida e volta e a final em jogo único"""
        dt = calendario.datas(self.e["ano"])["copa-do-brasil"]
        s = self.e["series"]
        f = c["fases"][k]
        ws = self.vencedores(f)
        A, B = s["A"], s["B"]
        if k == 0:
            return self._mata("2ª fase", self._pareados(ws + B[2:]), dt["fase2"], vantagem=True)
        if k == 1:
            return self._mata("3ª fase", self._sorteio(ws + B[:2] + A[10:], potes=True), dt["fase3"])
        if k == 2:
            return self._mata("4ª fase", self._sorteio(ws + A[6:10], potes=True), dt["fase4"])
        if k == 3:
            return self._mata("Oitavas", self._sorteio(ws + A[:6], potes=True), dt["oitavas"])
        if f["nome"] == "Oitavas":
            return self._mata("Quartas", self._sorteio(ws), dt["quartas"])
        if f["nome"] == "Quartas":
            return self._mata("Semifinal", self._sorteio(ws), dt["semifinal"])
        if f["nome"] == "Semifinal":
            return self._mata("Final", self._sorteio(ws), dt["final"], neutro=True)
        return self._campeao(c, ws[0])

    # ---- fim de temporada ----

    def _fim_de_temporada(self):
        """acesso e rebaixamento (4 entre todas as séries) e a próxima temporada"""
        e = self.e
        cs = e["comps"]
        A, B = cs["serie-a"]["final"], cs["serie-b"]["final"]
        C1 = cs["serie-c"]["primeira"]
        c_sobem = cs["serie-c"]["sobem"]
        d_sobem = cs["serie-d"]["sobem"]
        c_caem = C1[-SOBEM:]
        resumo = {"ano": e["ano"], "campeoes": {cid: c["campeao"] for cid, c in cs.items()},
                  "posicao": self._posicao_final(e["clube"])}
        e["historico"].append(resumo)
        nova = {
            "A": A[:-SOBEM] + B[:SOBEM],
            "B": A[-SOBEM:] + B[SOBEM:-SOBEM] + c_sobem,
            "C": B[-SOBEM:] + [t for t in self._ordem_c() if t not in c_sobem and t not in c_caem] + d_sobem,
            "D": c_caem + [t for t in self._ordem_d() if t not in d_sobem],
        }
        # cada série na ordem do ranking da próxima Copa: quem caiu na frente, quem subiu atrás
        e["series"] = nova
        self.noticia("Fim da temporada %d. %s" % (e["ano"], self._resumo_meu(nova)))
        e["ano"] += 1
        self._temporada()

    def _ordem_c(self):
        c = self.e["comps"]["serie-c"]
        return c["primeira"]

    def _ordem_d(self):
        f = self.e["comps"]["serie-d"]["fases"][0]
        linhas = []
        for g in range(len(f["grupos"])):
            linhas += [(i, r) for i, r in enumerate(motor.tabela(f["grupos"][g], [self.partida(p) for p in f["partidas"]]))]
        linhas.sort(key=lambda x: (x[0], -x[1]["pts"], -(x[1]["gp"] - x[1]["gc"])))
        return [r["clube"] for _i, r in linhas]

    def _posicao_final(self, t):
        s = self.serie_de(t)
        cid = "serie-" + s.lower()
        c = self.e["comps"][cid]
        if s in ("A", "B"):
            return "%dº na Série %s" % (c["final"].index(t) + 1, s)
        if s == "C":
            return "%dº na primeira fase da Série C" % (c["primeira"].index(t) + 1)
        return "Série D"

    def _resumo_meu(self, nova):
        t = self.e["clube"]
        antes, depois = self.serie_de(t), next(s for s, v in nova.items() if t in v)
        if depois < antes:
            return "%s sobe para a Série %s!" % (self.nome(t), depois)
        if depois > antes:
            return "%s cai para a Série %s." % (self.nome(t), depois)
        return "%s segue na Série %s." % (self.nome(t), depois)
