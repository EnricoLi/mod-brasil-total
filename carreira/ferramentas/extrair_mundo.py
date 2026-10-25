"""python extrair_mundo.py <pasta do mundo> <ferramentas do Mod Studio> <saida.json>

Lê um mundo do FL26 Mod Studio (livecpk/_FL26...) e escreve o retrato que o programa de
carreira usa: os clubes das Séries A a D com id do jogo, nome, sigla e elenco (id, nome,
posição, idade, overall como o jogo mostra)."""
import json, os, sys

world, tools, out = sys.argv[1:4]
sys.path.insert(0, tools)
import mkleague as M
import mkworld as W
import lbrating
import playeredit as E

db = os.path.join(world, "common", "etc", "pesdb")
plan = json.load(open(os.path.join(world, "leaguebuilder-plan.json"), encoding="utf-8"))

# as Séries A e B são as ligas do jogo (regulamentos 29 e 163); C e D, as do mundo
regs = M.load(db, "CompetitionRegulation.bin")
cid_of = {}
for i in range(len(regs) // M.REG):
    r = regs[i * M.REG:(i + 1) * M.REG]
    cid_of[int.from_bytes(r[M.R_ID:M.R_ID + 2], "little")] = r[M.R_CID]
ents = M.load(db, "CompetitionEntry.bin")


def entrants(cid):
    got = []
    for i in range(len(ents) // M.ENT):
        e = ents[i * M.ENT:(i + 1) * M.ENT]
        if e[M.E_CID] == cid:
            got.append((e[M.E_ORDER], int.from_bytes(e[M.E_TEAM:M.E_TEAM + 4], "little")))
    return [t for _o, t in sorted(got)]


series = {"A": entrants(cid_of[29]), "B": entrants(cid_of[163])}
for L in plan["leagues"]:
    series["C" if L["rid"] == 11 else "D"] = list(L["teams"])

_, teams = E.load(db, "Team.bin")
names = {}
for i in range(len(teams) // W.T_REC):
    t = teams[i * W.T_REC:(i + 1) * W.T_REC]
    names[int.from_bytes(t[W.T_ID:W.T_ID + 4], "little")] = E.cstr(t[W.T_NAME:W.T_NAME + W.T_NAME_LEN])

_, players = E.load(db, "Player.bin")
_, assigns = E.load(db, "PlayerAssignment.bin")
squad = {}
for i in range(len(assigns) // E.A_REC):
    o = i * E.A_REC
    tid, pid, pack = (E.u32(assigns, o + x) for x in (E.A_TID, E.A_PID, E.A_PACK))
    squad.setdefault(tid, []).append((pid, (pack & E.ORDER_MASK) >> E.ORDER_SHIFT, E.shirt_of(pack)))
index = {E.u32(players, i * E.P_REC + E.P_ID): i * E.P_REC for i in range(len(players) // E.P_REC)}


def player(pid, order, shirt):
    rec = players[index[pid]:index[pid] + E.P_REC]
    row = {n: E.show(n, E.getf(rec, n)) for n in E.FIELDS}
    return {"id": pid, "nome": E.cstr(rec[E.P_NAME:E.P_NAME + E.P_NAME_LEN]), "pos": row.get("Registered Position"),
            "idade": int(row["Age"]) if str(row.get("Age", "")).isdigit() else None,
            "overall": lbrating.rating(row), "ordem": order, "camisa": shirt}


clubes = []
for s, tids in series.items():
    for tid in tids:
        el = sorted((player(p, o, sh) for p, o, sh in squad.get(tid, []) if p in index), key=lambda p: p["ordem"])
        clubes.append({"id": tid, "nome": names.get(tid, str(tid)), "serie": s, "elenco": el})
json.dump({"fonte": os.path.basename(world.rstrip("/\\")), "clubes": clubes}, open(out, "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("%d clubes: %s" % (len(clubes), ", ".join("%s %d" % (s, len(t)) for s, t in series.items())))
