#!/usr/bin/env python3
"""Tests for datalog.py: parser, safety, stratification, semi-naive
evaluation, stratified negation, and the two café programs."""

import os
import unittest

from datalog import (
    parse, run_program, stratify, stable_models, well_founded, magic_query,
    SafetyError, StratificationError,
)


def query_atom(q):
    return parse(q + ".")[0].head

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, "programs", name)) as fh:
        return fh.read()


def chain(n):
    """edge facts for a chain n1 -> n2 -> ... -> n<n>."""
    return "".join("edge(n%d, n%d)." % (i, i + 1) for i in range(1, n))


class ParserTests(unittest.TestCase):
    def test_facts_rules_comments(self):
        clauses = parse("""
            % a comment
            parent(tom, bob).   # another comment
            age(tom, 42).
            likes("Mary Jane", pizza).
            rainy.
            wet :- rainy.
            grand(X, Z) :- parent(X, Y), parent(Y, Z).
        """)
        self.assertEqual(len(clauses), 6)
        self.assertEqual(str(clauses[-1]),
                         "grand(X, Z) :- parent(X, Y), parent(Y, Z).")
        self.assertEqual(clauses[1].head.args[1].value, 42)
        self.assertEqual(clauses[2].head.args[0].value, "Mary Jane")

    def test_zero_arity_and_negation(self):
        engine = run_program("rainy. dry :- not rainy. wet :- rainy.")
        self.assertEqual(engine.rels["wet"], {()})
        self.assertEqual(engine.rels.get("dry", set()), set())


class SafetyTests(unittest.TestCase):
    def test_arity_mismatch(self):
        with self.assertRaises(SafetyError):
            run_program("p(a). p(a, b).")

    def test_unbound_head_variable(self):
        with self.assertRaises(SafetyError):
            run_program("q(a). p(X) :- q(Y).")

    def test_unbound_negated_variable(self):
        with self.assertRaises(SafetyError):
            run_program("q(a). p(X) :- q(X), not r(X, Y).")

    def test_nonground_fact(self):
        with self.assertRaises(SafetyError):
            run_program("p(X).")


class StratificationTests(unittest.TestCase):
    def test_win_move_rejected(self):
        with self.assertRaises(StratificationError) as cm:
            run_program("move(a, b). win(X) :- move(X, Y), not win(Y).")
        self.assertIn("win", str(cm.exception))
        self.assertIn(("win", "win", True), cm.exception.cycle)

    def test_negation_over_lower_stratum_ok(self):
        engine = run_program("""
            node(a). node(b). node(c). node(d).
            edge(a, b). edge(b, c).
            reach(a).
            reach(Y) :- reach(X), edge(X, Y).
            unreached(X) :- node(X), not reach(X).
        """)
        self.assertEqual(engine.rels["reach"], {("a",), ("b",), ("c",)})
        self.assertEqual(engine.rels["unreached"], {("d",)})
        strata = engine.program.strata
        self.assertLess(strata["reach"], strata["unreached"])


class SemiNaiveTests(unittest.TestCase):
    def test_transitive_closure_deltas_shrink(self):
        engine = run_program(chain(10) + """
            path(X, Y) :- edge(X, Y).
            path(X, Z) :- edge(X, Y), path(Y, Z).
        """)
        self.assertEqual(len(engine.rels["path"]), 45)  # 10*9/2 pairs
        rounds = [sum(r.values()) for r in engine.stats[0]["iterations"]]
        # one new path length per round, strictly shrinking deltas
        self.assertEqual(rounds, [9, 8, 7, 6, 5, 4, 3, 2, 1, 0])

    def test_nonlinear_recursion_joins_delta_with_new_facts(self):
        # path(X,Z) :- path(X,Y), path(Y,Z) doubles path lengths per round;
        # this catches the classic semi-naive bug of missing delta-x-delta
        # combinations.
        engine = run_program(chain(9) + """
            path(X, Y) :- edge(X, Y).
            path(X, Z) :- path(X, Y), path(Y, Z).
        """)
        self.assertEqual(len(engine.rels["path"]), 36)  # 9*8/2 pairs
        # doubling needs far fewer rounds than the 9 a linear rule needs
        self.assertLess(len(engine.stats[0]["iterations"]), 8)

    def test_facts_seed_recursive_predicate(self):
        engine = run_program("""
            reach(a).
            edge(a, b). edge(b, c).
            reach(Y) :- reach(X), edge(X, Y).
        """)
        self.assertEqual(engine.rels["reach"], {("a",), ("b",), ("c",)})


class ClassicExamplesTests(unittest.TestCase):
    """The canonical example programs of the Datalog literature."""

    def test_ancestor(self):
        text = """
            parent(abe, bob). parent(bob, carl). parent(carl, dee).
            ancestor(X, Y) :- parent(X, Y).
            ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z).
        """
        engine = run_program(text)
        self.assertEqual(engine.rels["ancestor"], {
            ("abe", "bob"), ("abe", "carl"), ("abe", "dee"),
            ("bob", "carl"), ("bob", "dee"), ("carl", "dee")})
        # goal-directed: only bob's descendants are derived
        mengine, answers = magic_query(parse(text),
                                       query_atom("ancestor(bob, X)"))
        self.assertEqual(answers, {("bob", "carl"), ("bob", "dee")})
        self.assertEqual(len(mengine.rels["ancestor#bf"]), 3)  # not 6

    def test_same_generation(self):
        # the classic magic-sets benchmark: cal and dee are cousins
        text = """
            person(pam). person(ann). person(bob). person(cal). person(dee).
            parent(ann, pam). parent(bob, pam).
            parent(cal, ann). parent(dee, bob).
            sg(X, X) :- person(X).
            sg(X, Y) :- parent(X, XP), parent(Y, YP), sg(XP, YP).
        """
        engine = run_program(text)
        self.assertEqual(
            {t for t in engine.rels["sg"] if t[0] != t[1]},
            {("ann", "bob"), ("bob", "ann"), ("cal", "dee"), ("dee", "cal")})
        _m, answers = magic_query(parse(text), query_atom("sg(cal, Y)"))
        self.assertEqual(answers, {("cal", "cal"), ("cal", "dee")})

    def test_tweety_default_reasoning(self):
        # birds fly unless known to be abnormal; penguins are abnormal
        engine = run_program("""
            bird(tweety). bird(opus). penguin(opus).
            abnormal(X) :- penguin(X).
            flies(X) :- bird(X), not abnormal(X).
        """)
        self.assertEqual(engine.rels["flies"], {("tweety",)})

    def test_barber_paradox(self):
        # the barber shaves exactly those who do not shave themselves
        text = """
            person(barber). person(plato).
            shaves(barber, X) :- person(X), not shaves(X, X).
        """
        with self.assertRaises(StratificationError):
            run_program(text)
        clauses = parse(text)
        self.assertEqual(stable_models(clauses), [])
        true, undef = well_founded(clauses)
        self.assertEqual(undef, {("shaves", ("barber", "barber"))})
        self.assertIn(("shaves", ("barber", "plato")), true)

    def test_even_odd_mutual_recursion(self):
        engine = run_program("""
            edge(n1, n2). edge(n2, n3). edge(n3, n4). edge(n4, n5).
            odd(X, Y)  :- edge(X, Y).
            odd(X, Y)  :- even(X, Z), edge(Z, Y).
            even(X, Y) :- odd(X, Z), edge(Z, Y).
        """)
        self.assertEqual(engine.rels["odd"], {
            ("n1", "n2"), ("n2", "n3"), ("n3", "n4"), ("n4", "n5"),
            ("n1", "n4"), ("n2", "n5")})
        self.assertEqual(engine.rels["even"], {
            ("n1", "n3"), ("n2", "n4"), ("n3", "n5"), ("n1", "n5")})
        strata = engine.program.strata
        self.assertEqual(strata["odd"], strata["even"])

    def test_andersen_points_to(self):
        # field-insensitive Andersen-style pointer analysis:
        # v1 = new h1; v2 = new h2; v3 = v1; *v3 = v2; v4 = *v3
        engine = run_program("""
            alloc(v1, h1). alloc(v2, h2).
            assign(v3, v1).
            store(v3, v2).
            load(v4, v3).
            pt(V, H) :- alloc(V, H).
            pt(V, H) :- assign(V, W), pt(W, H).
            hpt(H1, H2) :- store(P, W), pt(P, H1), pt(W, H2).
            pt(V, H2) :- load(V, P), pt(P, H1), hpt(H1, H2).
        """)
        self.assertEqual(engine.rels["pt"], {
            ("v1", "h1"), ("v2", "h2"), ("v3", "h1"), ("v4", "h2")})
        self.assertEqual(engine.rels["hpt"], {("h1", "h2")})


class MagicSetTests(unittest.TestCase):
    TC = """
        path(X, Y) :- edge(X, Y).
        path(X, Z) :- edge(X, Y), path(Y, Z).
    """

    def test_bound_first_argument_prunes_derivation(self):
        clauses = parse(chain(10) + self.TC)
        engine, answers = magic_query(clauses, query_atom("path(n5, X)"))
        self.assertEqual(answers,
                         {("n5", "n%d" % j) for j in range(6, 11)})
        # only paths reachable from the demanded start points are derived:
        # pairs within n5..n10 (15) instead of the full closure (45)
        self.assertEqual(len(engine.rels["path#bf"]), 15)
        self.assertEqual(engine.rels["magic#path#bf"],
                         {("n%d" % i,) for i in range(5, 11)})

    def test_bound_second_argument_uses_multiple_adornments(self):
        clauses = parse(chain(10) + self.TC)
        _engine, answers = magic_query(clauses, query_atom("path(X, n10)"))
        self.assertEqual(answers,
                         {("n%d" % i, "n10") for i in range(1, 10)})

    def test_matches_full_evaluation_with_negation_fallback(self):
        text = """
            node(a). node(b). node(c). node(d).
            edge(a, b). edge(b, c).
            reach(a).
            reach(Y) :- reach(X), edge(X, Y).
            unreached(X) :- node(X), not reach(X).
        """
        _engine, answers = magic_query(parse(text), query_atom("unreached(X)"))
        self.assertEqual(answers, {("d",)})

    def test_idb_facts_survive_the_rewriting(self):
        text = """
            reach(a).
            edge(a, b). edge(b, c).
            reach(Y) :- reach(X), edge(X, Y).
        """
        _engine, answers = magic_query(parse(text), query_atom("reach(X)"))
        self.assertEqual(answers, {("a",), ("b",), ("c",)})

    def test_edb_query_passes_through(self):
        clauses = parse(chain(10) + self.TC)
        _engine, answers = magic_query(clauses, query_atom("edge(n1, X)"))
        self.assertEqual(answers, {("n1", "n2")})

    def test_cafe_foodary_magic_matches_full(self):
        clauses = parse(load("cafe_foodary.dl"))
        _engine, answers = magic_query(clauses, query_atom("eats_in_cafe(X)"))
        self.assertEqual(answers, {("bob",), ("carol",)})

    def test_cafe_paradox_still_rejected_under_magic(self):
        # the negated subgoal pulls in the original cycle untransformed
        clauses = parse(load("cafe_paradox.dl"))
        with self.assertRaises(StratificationError):
            magic_query(clauses, query_atom("eats_at_home(alice)"))


class SemanticsTests(unittest.TestCase):
    """Stratifiability is syntactic; these tests check the semantic layer
    (stable models, well-founded model) and that the two are not conflated."""

    def test_unstratifiable_program_can_still_have_stable_models(self):
        # The standard example: unstratifiable, yet two stable models.
        clauses = parse(
            "move(a, b). move(b, a). win(X) :- move(X, Y), not win(Y).")
        with self.assertRaises(StratificationError):
            stratify(clauses)
        models = stable_models(clauses)
        win_parts = sorted(tuple(sorted(a for a in m if a[0] == "win"))
                           for m in models)
        self.assertEqual(win_parts,
                         [(("win", ("a",)),), (("win", ("b",)),)])

    def test_p_not_p_has_no_stable_model_and_is_wfs_undefined(self):
        clauses = parse("p :- not p.")
        self.assertEqual(stable_models(clauses), [])
        _true, undef = well_founded(clauses)
        self.assertEqual(undef, {("p", ())})

    def test_stratified_program_has_exactly_its_stratified_model(self):
        text = load("cafe_foodary.dl")
        engine = run_program(text)
        models = stable_models(parse(text))
        self.assertEqual(len(models), 1)
        expected = {(p, t) for p, ts in engine.rels.items() for t in ts}
        self.assertEqual(models[0], expected)


class CafeTests(unittest.TestCase):
    def test_paradox_is_rejected_as_unstratifiable(self):
        with self.assertRaises(StratificationError) as cm:
            run_program(load("cafe_paradox.dl"))
        msg = str(cm.exception)
        self.assertIn("eats_in_cafe", msg)
        self.assertIn("household_cooks", msg)
        # the offending cycle is negation through recursion between the two
        preds = {p for edge in cm.exception.cycle for p in edge[:2]}
        self.assertEqual(preds, {"eats_in_cafe", "household_cooks"})

    def test_paradox_has_no_stable_model(self):
        # The semantic verdict behind the syntactic rejection: this
        # particular program really is paradoxical — no stable model.
        self.assertEqual(stable_models(parse(load("cafe_paradox.dl"))), [])

    def test_paradox_wfs_leaves_exactly_bobs_atoms_undefined(self):
        true, undef = well_founded(parse(load("cafe_paradox.dl")))
        self.assertEqual(undef, {
            ("household_cooks", ("cafe_house",)),
            ("eats_at_home", ("bob",)),
            ("eats_in_cafe", ("bob",)),
        })
        # everyone else's meals are settled
        self.assertIn(("household_cooks", ("house_a",)), true)
        self.assertIn(("eats_at_home", ("alice",)), true)
        self.assertIn(("eats_at_home", ("alan",)), true)
        self.assertIn(("eats_in_cafe", ("carol",)), true)

    def test_constraint_reading_is_stratified_and_flags_only_bob(self):
        # Direct reading: household_cooks derived outright, the
        # program stratifies, and the paradox appears as a data-level
        # integrity violation naming exactly Bob.
        engine = run_program(load("cafe_constraint.dl"))
        self.assertEqual(engine.rels["household_cooks"],
                         {("house_a",), ("cafe_house",)})
        self.assertEqual(engine.rels["eats_at"], {
            ("alice", "house_a"), ("alan", "house_a"),
            ("bob", "cafe_house"), ("carol", "cafe_house")})
        self.assertEqual(engine.rels["violation"], {("bob",)})

    def test_foodary_model_lets_bob_eat_in_the_cafe(self):
        engine = run_program(load("cafe_foodary.dl"))
        self.assertEqual(engine.rels["household_cooks"], {("house_a",)})
        self.assertEqual(engine.rels["eats_at_home"], {("alice",), ("alan",)})
        self.assertEqual(engine.rels["eats_in_cafe"], {("bob",), ("carol",)})
        # the policy's two conclusions hold: no violations derived
        self.assertEqual(engine.rels.get("conclusion1_violated", set()), set())
        self.assertEqual(engine.rels.get("conclusion2_violated", set()), set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
