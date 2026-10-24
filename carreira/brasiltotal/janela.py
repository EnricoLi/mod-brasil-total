"""A janela do programa: a carreira, os jogos que você joga no PES e o resto simulado."""
import datetime, json, os, sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QListWidget, QMainWindow, QMessageBox,
                               QPushButton, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .carreira import Carreira, NOMES, SERIES
from . import motor

ESTILO = """
QWidget { background: #14171c; color: #e6e6e6; font-size: 14px; }
QPushButton { background: #232831; border: 1px solid #343b47; padding: 8px 14px; border-radius: 4px; }
QPushButton:hover { background: #2c333e; }
QPushButton#principal { background: #1f6feb; border-color: #1f6feb; font-weight: bold; }
QPushButton#nav { text-align: left; border: none; padding: 10px 14px; background: transparent; }
QPushButton#nav:checked { background: #232831; color: #f0b429; }
QTableWidget, QTreeWidget, QListWidget { background: #181c22; gridline-color: #2a303a; border: 1px solid #2a303a; }
QHeaderView::section { background: #1d222a; color: #aab; border: none; padding: 6px; }
QComboBox, QSpinBox { background: #1d222a; border: 1px solid #343b47; padding: 4px 8px; }
QFrame#cartao { background: #1a1f26; border: 1px solid #2a303a; border-radius: 6px; }
QLabel { background: transparent; }
QLabel#jogo { font-size: 24px; font-weight: bold; }
QLabel#titulo { font-size: 22px; font-weight: bold; color: #f0b429; }
QLabel#sub { color: #9aa3b2; }
"""


def data_br(iso):
    d = datetime.date.fromisoformat(iso)
    dias = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    return "%s %02d/%02d/%d" % (dias[d.weekday()], d.day, d.month, d.year)


def pasta_dados():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    p = os.path.join(base, "BrasilTotal")
    os.makedirs(p, exist_ok=True)
    return p


def item(t, centro=False, cor=None):
    it = QTableWidgetItem(str(t))
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    if centro:
        it.setTextAlignment(Qt.AlignCenter)
    if cor:
        it.setForeground(QColor(cor))
    return it


class NovaCarreira(QDialog):
    def __init__(self, mundo, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova carreira")
        self.resize(560, 640)
        v = QVBoxLayout(self)
        t = QLabel("Escolha o seu clube")
        t.setObjectName("titulo")
        v.addWidget(t)
        self.serie = QComboBox()
        self.serie.addItems(["Série %s" % s for s in SERIES])
        v.addWidget(self.serie)
        self.lista = QListWidget()
        v.addWidget(self.lista, 1)
        self.mundo = mundo
        self.serie.currentIndexChanged.connect(self.encher)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Começar")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.encher()

    def encher(self):
        s = SERIES[self.serie.currentIndex()]
        cs = sorted((c for c in self.mundo["clubes"] if c["serie"] == s), key=lambda c: -motor.forca(c))
        self.lista.clear()
        self.ids = []
        for c in cs:
            self.lista.addItem("%s   (força %.1f)" % (c["nome"], motor.forca(c)))
            self.ids.append(c["id"])
        self.lista.setCurrentRow(0)

    def escolhido(self):
        r = self.lista.currentRow()
        return self.ids[r] if r >= 0 else None


class Janela(QMainWindow):
    def __init__(self, mundo, salvo):
        super().__init__()
        self.mundo, self.salvo = mundo, salvo
        self.c = None
        self.pendente = None
        self.setWindowTitle("Brasil Total — Carreira")
        self.resize(1180, 760)
        raiz = QWidget()
        self.setCentralWidget(raiz)
        h = QHBoxLayout(raiz)
        h.setContentsMargins(0, 0, 0, 0)
        nav = QVBoxLayout()
        nav.setContentsMargins(8, 12, 8, 12)
        self.paginas = QStackedWidget()
        self.botoes = []
        for i, (nome, fab) in enumerate((("Início", self.pag_inicio), ("Calendário", self.pag_calendario),
                                         ("Tabelas", self.pag_tabelas), ("Copa do Brasil", self.pag_copa),
                                         ("Elenco", self.pag_elenco), ("Notícias", self.pag_noticias))):
            b = QPushButton(nome)
            b.setObjectName("nav")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=i: self.ir(k))
            nav.addWidget(b)
            self.botoes.append(b)
            self.paginas.addWidget(fab())
        nav.addStretch(1)
        nb = QPushButton("Nova carreira")
        nb.clicked.connect(self.nova)
        nav.addWidget(nb)
        lado = QWidget()
        lado.setLayout(nav)
        lado.setFixedWidth(190)
        h.addWidget(lado)
        h.addWidget(self.paginas, 1)
        if os.path.exists(salvo):
            try:
                self.c = Carreira.carregar(salvo, mundo)
            except Exception as e:                 # um salvo que não lê: começa de novo
                QMessageBox.warning(self, "Carreira", "Não deu para abrir a carreira salva: %s" % e)
        if self.c is None:
            self.nova(primeira=True)
        else:
            self.pendente = self._pendente_salva()
        self.ir(0)

    # ---- carreira ----

    def _pendente_salva(self):
        m = self.c.proximo_jogo()
        return m if m and m["data"] == self.c.e["data"] else None

    def nova(self, primeira=False):
        d = NovaCarreira(self.mundo, self)
        if d.exec() != QDialog.Accepted or d.escolhido() is None:
            if primeira:
                sys.exit(0)
            return
        if self.c is not None and QMessageBox.question(self, "Nova carreira", "Apagar a carreira atual e começar outra?") != QMessageBox.Yes:
            return
        self.c = Carreira.nova(self.mundo, d.escolhido())
        self.pendente = None
        self.salvar()
        self.atualizar()

    def salvar(self):
        self.c.salvar(self.salvo)

    def ir(self, k):
        for i, b in enumerate(self.botoes):
            b.setChecked(i == k)
        self.paginas.setCurrentIndex(k)
        self.atualizar()

    def atualizar(self):
        if self.c is None:
            return
        k = self.paginas.currentIndex()
        [self.encher_inicio, self.encher_calendario, self.encher_tabelas, self.encher_copa,
         self.encher_elenco, self.encher_noticias][k]()

    # ---- Início ----

    def pag_inicio(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 20, 24, 20)
        self.i_titulo = QLabel()
        self.i_titulo.setObjectName("titulo")
        self.i_sub = QLabel()
        self.i_sub.setObjectName("sub")
        v.addWidget(self.i_titulo)
        v.addWidget(self.i_sub)
        card = QFrame()
        card.setObjectName("cartao")
        g = QGridLayout(card)
        g.setContentsMargins(20, 16, 20, 16)
        self.i_comp = QLabel()
        self.i_comp.setObjectName("sub")
        self.i_jogo = QLabel()
        self.i_jogo.setObjectName("jogo")
        self.i_info = QLabel()
        self.i_info.setWordWrap(True)
        g.addWidget(self.i_comp, 0, 0, 1, 4)
        g.addWidget(self.i_jogo, 1, 0, 1, 4)
        g.addWidget(self.i_info, 2, 0, 1, 4)
        self.i_gc, self.i_gf = QSpinBox(), QSpinBox()
        for s in (self.i_gc, self.i_gf):
            s.setRange(0, 30)
            s.setFixedWidth(70)
        self.i_lc, self.i_lf = QLabel(), QLabel()
        g.addWidget(self.i_lc, 3, 0)
        g.addWidget(self.i_gc, 3, 1)
        g.addWidget(self.i_lf, 4, 0)
        g.addWidget(self.i_gf, 4, 1)
        self.i_lpen = QLabel("Venceu nos pênaltis:")
        self.i_pen = QComboBox()
        g.addWidget(self.i_lpen, 5, 0)
        g.addWidget(self.i_pen, 5, 1, 1, 2)
        bl = QHBoxLayout()
        self.i_conf = QPushButton("Confirmar placar do PES")
        self.i_conf.setObjectName("principal")
        self.i_conf.clicked.connect(self.confirmar)
        self.i_sim = QPushButton("Simular este jogo")
        self.i_sim.clicked.connect(self.simular_meu)
        bl.addWidget(self.i_conf)
        bl.addWidget(self.i_sim)
        bl.addStretch(1)
        g.addLayout(bl, 6, 0, 1, 4)
        v.addWidget(card)
        self.i_gc.valueChanged.connect(self._pen_visivel)
        self.i_gf.valueChanged.connect(self._pen_visivel)
        av = QHBoxLayout()
        self.i_avancar = QPushButton("Avançar até o próximo jogo")
        self.i_avancar.setObjectName("principal")
        self.i_avancar.clicked.connect(self.avancar)
        av.addWidget(self.i_avancar)
        av.addStretch(1)
        v.addLayout(av)
        t = QLabel("Últimas notícias")
        t.setObjectName("sub")
        v.addWidget(t)
        self.i_news = QListWidget()
        v.addWidget(self.i_news, 1)
        return w

    def encher_inicio(self):
        c = self.c
        me = c.e["clube"]
        s = c.serie_de(me)
        self.i_titulo.setText(c.nome(me))
        self.i_sub.setText("Temporada %d · Série %s · %s" % (c.e["ano"], s, data_br(c.e["data"])))
        m = self.pendente
        jogar = m is not None
        for x in (self.i_gc, self.i_gf, self.i_lc, self.i_lf, self.i_conf, self.i_sim):
            x.setVisible(jogar)
        self.i_avancar.setEnabled(not jogar)
        prox = m or c.proximo_jogo()
        if prox is None:
            self.i_comp.setText("")
            self.i_jogo.setText("Sem jogos marcados")
            self.i_info.setText("Avance para fechar a temporada.")
        else:
            f = c.e["comps"][prox["comp"]]["fases"][prox["fase"]]
            extra = (" · rodada %d" % prox["rodada"]) if prox.get("rodada") else ""
            self.i_comp.setText("%s · %s%s · %s" % (NOMES[prox["comp"]], f["nome"], extra, data_br(prox["data"])))
            self.i_jogo.setText("%s  x  %s" % (c.nome(prox["casa"]), c.nome(prox["fora"])))
            if jogar:
                dica = ("No PES 2021: Amistoso (Exhibition), %s como mandante e %s como visitante. "
                        "Jogue e digite o placar final aqui (sem os pênaltis)." % (c.nome(prox["casa"]), c.nome(prox["fora"])))
                if prox.get("vantagem"):
                    dica += " Empate classifica %s." % c.nome(prox["vantagem"])
                self.i_info.setText(dica)
                self.i_lc.setText(c.nome(prox["casa"]))
                self.i_lf.setText(c.nome(prox["fora"]))
                self.i_gc.setValue(0)
                self.i_gf.setValue(0)
                self.i_pen.clear()
                self.i_pen.addItem(c.nome(prox["casa"]), prox["casa"])
                self.i_pen.addItem(c.nome(prox["fora"]), prox["fora"])
            else:
                self.i_info.setText("Força: %s %.1f · %s %.1f" % (c.nome(prox["casa"]), c.forca(prox["casa"]),
                                                                  c.nome(prox["fora"]), c.forca(prox["fora"])))
        self._pen_visivel()
        self.i_news.clear()
        for n in c.e["noticias"][:30]:
            self.i_news.addItem("%s  %s" % (data_br(n["data"])[4:], n["texto"]))

    def _pen_visivel(self):
        m = self.pendente
        mostra = False
        if m is not None:
            gc, gf = m["gc"], m["gf"]
            m["gc"], m["gf"] = self.i_gc.value(), self.i_gf.value()
            mostra = self.c.precisa_penaltis(m)
            m["gc"], m["gf"] = gc, gf
        self.i_lpen.setVisible(mostra)
        self.i_pen.setVisible(mostra)

    def avancar(self):
        self.pendente = self.c.avancar()
        self.salvar()
        self.atualizar()

    def confirmar(self):
        m = self.pendente
        pen = self.i_pen.currentData() if self.i_pen.isVisible() else None
        try:
            self.c.registrar(m["id"], self.i_gc.value(), self.i_gf.value(), pen)
        except ValueError as e:
            QMessageBox.warning(self, "Placar", str(e))
            return
        self.pendente = None
        self.salvar()
        self.atualizar()

    def simular_meu(self):
        m = self.pendente
        self.c.simular_meu(m["id"])
        m = self.c.partida(m["id"])
        self.pendente = None
        self.salvar()
        QMessageBox.information(self, "Simulado", "%s %d x %d %s" % (self.c.nome(m["casa"]), m["gc"], m["gf"], self.c.nome(m["fora"])))
        self.atualizar()

    # ---- Calendário ----

    def pag_calendario(self):
        self.cal = QTableWidget(0, 5)
        self.cal.setHorizontalHeaderLabels(["Data", "Competição", "Fase", "Jogo", "Placar"])
        self.cal.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.cal.verticalHeader().setVisible(False)
        return self._moldura("Calendário do seu clube", self.cal)

    def encher_calendario(self):
        c = self.c
        ms = c.partidas_de()
        self.cal.setRowCount(len(ms))
        for r, m in enumerate(ms):
            f = c.e["comps"][m["comp"]]["fases"][m["fase"]]
            self.cal.setItem(r, 0, item(data_br(m["data"])))
            self.cal.setItem(r, 1, item(NOMES[m["comp"]]))
            self.cal.setItem(r, 2, item(f["nome"] + (" %d" % m["rodada"] if m.get("rodada") else "")))
            self.cal.setItem(r, 3, item("%s x %s" % (c.nome(m["casa"]), c.nome(m["fora"]))))
            self.cal.setItem(r, 4, item(self._placar(m), True))
        self.cal.resizeColumnsToContents()
        self.cal.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

    def _placar(self, m):
        if m["gc"] is None:
            return ""
        p = "%d x %d" % (m["gc"], m["gf"])
        if m.get("pen"):
            p += " (pên. %s)" % self.c.nome(m["pen"])
        return p

    # ---- Tabelas ----

    def pag_tabelas(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 20, 24, 20)
        t = QLabel("Tabelas")
        t.setObjectName("titulo")
        v.addWidget(t)
        self.t_sel = QComboBox()
        self.t_sel.currentIndexChanged.connect(lambda _i: self._tabela())
        v.addWidget(self.t_sel)
        self.tab = QTableWidget(0, 10)
        self.tab.setHorizontalHeaderLabels(["#", "Clube", "P", "J", "V", "E", "D", "GP", "GC", "SG"])
        self.tab.verticalHeader().setVisible(False)
        v.addWidget(self.tab, 1)
        return w

    def encher_tabelas(self):
        c = self.c
        atual = self.t_sel.currentData()
        self.t_sel.blockSignals(True)
        self.t_sel.clear()
        for cid in ("serie-a", "serie-b", "serie-c", "serie-d"):
            for k, f in enumerate(c.e["comps"][cid]["fases"]):
                if f["tipo"] != "liga":
                    continue
                for g in range(len(f["grupos"])):
                    nome = NOMES[cid] + (" · " + f["nome"] if len(c.e["comps"][cid]["fases"]) > 1 or cid in ("serie-c", "serie-d") else "")
                    if len(f["grupos"]) > 1:
                        nome += " · Grupo %s" % "ABCD"[g]
                    self.t_sel.addItem(nome, (cid, k, g))
        meu = c.serie_de(c.e["clube"])
        i = self.t_sel.findData(atual) if atual else -1
        if i < 0:
            i = next((j for j in range(self.t_sel.count()) if self.t_sel.itemData(j)[0] == "serie-" + meu.lower()), 0)
        self.t_sel.setCurrentIndex(i)
        self.t_sel.blockSignals(False)
        self._tabela()

    def _tabela(self):
        d = self.t_sel.currentData()
        if not d:
            return
        cid, k, g = d
        linhas = self.c.tabela(cid, k, g)
        self.tab.setRowCount(len(linhas))
        for r, l in enumerate(linhas):
            cor = "#f0b429" if l["clube"] == self.c.e["clube"] else None
            vals = [r + 1, self.c.nome(l["clube"]), l["pts"], l["j"], l["v"], l["e"], l["d"], l["gp"], l["gc"], l["gp"] - l["gc"]]
            for col, x in enumerate(vals):
                self.tab.setItem(r, col, item(x, col != 1, cor))
        self.tab.resizeColumnsToContents()
        self.tab.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    # ---- Copa do Brasil ----

    def pag_copa(self):
        self.copa = QTreeWidget()
        self.copa.setHeaderLabels(["Confronto", "Jogos", "Classificado"])
        self.copa.header().setSectionResizeMode(0, QHeaderView.Stretch)
        return self._moldura("Copa do Brasil", self.copa)

    def encher_copa(self):
        c = self.c
        self.copa.clear()
        comp = c.e["comps"]["copa-do-brasil"]
        for f in comp["fases"]:
            top = QTreeWidgetItem(["%s — %s" % (f["nome"], ", ".join(data_br(d)[4:] for d in f["datas"]))])
            fb = top.font(0)
            fb.setBold(True)
            top.setFont(0, fb)
            self.copa.addTopLevelItem(top)
            for conf in f.get("confrontos") or []:
                js = [c.partida(p) for p in conf]
                w = motor.vencedor_confronto(js)
                nome = "%s x %s" % (c.nome(js[0]["casa"]), c.nome(js[0]["fora"]))
                placares = " · ".join(self._placar(j) or "-" for j in js)
                it = QTreeWidgetItem([nome, placares, c.nome(w) if w else ""])
                if c.e["clube"] in (js[0]["casa"], js[0]["fora"]):
                    for col in range(3):
                        it.setForeground(col, QColor("#f0b429"))
                top.addChild(it)
            top.setExpanded(True)
        if comp["campeao"]:
            self.copa.addTopLevelItem(QTreeWidgetItem(["Campeão: %s" % c.nome(comp["campeao"])]))
        self.copa.resizeColumnToContents(1)
        self.copa.resizeColumnToContents(2)

    # ---- Elenco ----

    def pag_elenco(self):
        self.el = QTableWidget(0, 5)
        self.el.setHorizontalHeaderLabels(["Nº", "Jogador", "Posição", "Idade", "Overall"])
        self.el.verticalHeader().setVisible(False)
        return self._moldura("Elenco", self.el)

    def encher_elenco(self):
        el = self.c.clubes[self.c.e["clube"]]["elenco"]
        self.el.setRowCount(len(el))
        for r, p in enumerate(el):
            for col, x in enumerate((p.get("camisa", ""), p["nome"], p.get("pos", ""), p.get("idade") or "", p["overall"])):
                self.el.setItem(r, col, item(x, col != 1))
        self.el.resizeColumnsToContents()
        self.el.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    # ---- Notícias ----

    def pag_noticias(self):
        self.news = QListWidget()
        return self._moldura("Notícias", self.news)

    def encher_noticias(self):
        self.news.clear()
        for n in self.c.e["noticias"]:
            self.news.addItem("%s  %s" % (data_br(n["data"]), n["texto"]))

    def _moldura(self, titulo, corpo):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 20, 24, 20)
        t = QLabel(titulo)
        t.setObjectName("titulo")
        v.addWidget(t)
        v.addWidget(corpo, 1)
        return w


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO)
    aqui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mundo_p = os.path.join(aqui, "dados", "mundo.json")
    if not os.path.exists(mundo_p):
        QMessageBox.critical(None, "Brasil Total", "Falta o arquivo %s" % mundo_p)
        return 1
    mundo = json.load(open(mundo_p, encoding="utf-8"))
    j = Janela(mundo, os.path.join(pasta_dados(), "carreira.json"))
    j.show()
    return app.exec()
