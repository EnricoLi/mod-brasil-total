"""python test_custom_cups.py <folder with the game's tables> -- the recipe's custom_cups: a
knockout of 16 laid out by hand, fed by league places and pre-round winners. plan() refuses a
cup it cannot build with a sentence that says what to change; Build writes one `ccup` line and
one `lpre` per pre-round, their ties the cup's entries, and keeps the ids on the next Build"""
import json, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leaguebuilder as B

A, S = 29, 163                         # the game's Brasileirão Série A and Série B


def cup(**kw):
    c = {"name": "Copa Teste", "country": "Brazil",
         "entry": [[S, 1], [S, 2]] + [x for k in range(7) for x in (["pre", 0, k], ["pre", 1, k])],
         "pre": [{"entry": [x for k in range(7) for x in ([S, 3 + k], [A, 1 + k])]},
                 {"entry": [x for k in range(7) for x in ([S, 10 + k], [A, 8 + k])]}]}
    c.update(kw)
    return c


def recipe(*cups):
    return {"world": "_FL26TestCustom", "leagues": [], "custom_cups": list(cups)}


def refused(base, c, words):
    try:
        B.plan(recipe(c), base)
    except B.BuildError as e:
        assert words in str(e), (words, str(e))
        print("ok refused: %s" % e)
        return
    raise AssertionError("plan() took a cup it should refuse (%s)" % words)


def lines(game):
    w = os.path.join(B.siderdir.find(game), "livecpk", "_FL26TestCustom")
    got = [l.strip() for l in open(os.path.join(w, B.MARK), encoding="utf-8") if l.startswith(("ccup ", "lpre ", "cupdays "))]
    return got, json.load(open(os.path.join(w, "leaguebuilder-plan.json"), encoding="utf-8"))


def main(base):
    assert B.has_edits(recipe(cup())), "a recipe with only custom_cups changes something"
    pl = B.plan(recipe(cup()), base)
    c = next(h for h in pl["home_cups"] if h["kind"] == "custom")
    assert c["opts"]["days"] == B.CUSTOM_CUP_DAYS and [q["days"] for q in c["opts"]["pre"]] == [B.CUSTOM_PRE_DAYS] * 2
    text = B.describe(pl)
    assert "Copa Teste: custom cup, a two-legged knockout of 16 clubs, 14 of them pre-round winners" in text, text
    assert "tie 0: Brasileirão Série B 3 v Brasileirão Série A 1" in text, text
    print("ok plan and its text")

    refused(base, cup(entry=cup()["entry"][:15]), "15 places -- the knockout has 16")
    refused(base, cup(pre=[{"entry": [[S, 3], [A, 1], [S, 4]]}] + cup()["pre"][1:]), "3 clubs -- a pre-round is 1 to 8 ties")
    refused(base, cup(entry=[[S, 1], [S, 2]] + [x for k in range(7) for x in (["pre", 0, k], ["pre", 0, k])]),
            "the winner of pre-round 0 tie 0 has two places")
    refused(base, cup(entry=[[S, 1], [S, 2], [S, 18], [S, 19]] + [x for k in range(6) for x in (["pre", 0, k], ["pre", 1, k])]),
            "the winners of pre-round 0 tie 6, pre-round 1 tie 6 have no place")
    refused(base, cup(entry=[[S, 3], [S, 2]] + cup()["entry"][2:]), "Brasileirão Série B 3 plays twice")
    refused(base, cup(entry=[["Nowhere League", 1]] + cup()["entry"][1:]), "no league 'Nowhere League'")
    refused(base, cup(entry=[[A, 21]] + cup()["entry"][1:]), "has 20 clubs, no position 21")
    refused(base, cup(days=[265, 279, 300, 321, 335, 356]), "6 days -- the knockout of 16 plays on 7")
    refused(base, cup(days=[265, 279, 300, 314, 321, 356, 335]), "are not one after the other")
    refused(base, cup(days=[265, 279, 300, 314, 321, 335, 10]), "day 10 is outside the cup's season")
    refused(base, cup(fill=240), "filled on day 240, but pre-round 0's second leg is day 244")
    refused(base, cup(country="Atlantis"), "no country called 'Atlantis'")

    game = tempfile.mkdtemp(prefix="customcup-")
    try:
        pl = B.plan(recipe(cup()), base)
        B.build(pl, base, game, replace=True, log=lambda *a: None)
        got, done = lines(game)
        ids = done["cup_ids"]["ccup:FL_CC1"]
        ko, p0, p1 = ids["ko"], ids["pre_reg"], ids["pre_reg2"]
        want = ["%d:%d" % (S, 1), "%d:%d" % (S, 2)] + ["%d:0" % (p + 1024 * (k + 1)) for k in range(7) for p in (p0, p1)]
        cl = [l for l in got if l.startswith("ccup ")]
        assert len(cl) == 1 and cl[0].startswith("ccup %d ko=%d groups=0 entry=%s fill=253 national=1 days=265,279,300,314,321,335,356 "
                                                 % (ko, ko, ",".join(want))), cl
        lp = [l for l in got if l.startswith("lpre ")]
        assert lp == ["lpre %d cup=%d fill=226 days=237,244 entry=%s" % (p, ko, ",".join(
            "%d:%d" % tuple(e) for e in q["entry"])) for p, q in zip((p0, p1), cup()["pre"])], lp
        assert "cupdays %d 237 244 265 279 300 314 321 335 356" % A in got, got
        print("ok world file:\n  " + "\n  ".join(cl + lp))

        # a league cup built in front of it now (game_cups): the first free ids go to that one,
        # and the custom cup keeps its own -- a career holds them
        pl = B.plan(dict(recipe(dict(cup(), name="Copa Teste II")), game_cups=[{"league": A}]), base, prev=done)
        B.build(pl, base, game, replace=True, log=lambda *a: None)
        _got, again = lines(game)
        assert again["cup_ids"]["ccup:FL_CC1"] == ids, (again["cup_ids"], ids)
        assert again["cup_ids"]["ccup:FL_G%03d_LCUP" % A]["cid"] != ids["cid"], again["cup_ids"]
        print("ok the next Build keeps competition %d and regulations %d, %d, %d" % (ids["cid"], ko, p0, p1))
    finally:
        shutil.rmtree(game, ignore_errors=True)
    print("all passed")


if __name__ == "__main__":
    main(sys.argv[1])
