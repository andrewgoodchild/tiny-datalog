#!/usr/bin/env python3
"""Tests for the whole repository: the core engine (parser, safety,
stratification, semi-naive, magic sets, stable/well-founded models), the
classic example programs, and the satellite modules (semiring.py,
incremental.py, prolog.py)."""

import os
import unittest

from datalog import (
    parse, run_program, stratify,
    Engine, Program, SafetyError, StratificationError, DatalogError,
)
from magic import magic_query
from semantics import stable_models, well_founded
from semiring import run_semiring
from incremental import IncrementalEngine
import prolog
import subsumption


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

    def test_shipped_reachability_program(self):
        engine = run_program(load("02-reachability.dl"))
        self.assertEqual(len(engine.rels["path"]), 35)

    def test_facts_seed_recursive_predicate(self):
        engine = run_program("""
            reach(a).
            edge(a, b). edge(b, c).
            reach(Y) :- reach(X), edge(X, Y).
        """)
        self.assertEqual(engine.rels["reach"], {("a",), ("b",), ("c",)})


class ClassicExamplesTests(unittest.TestCase):
    """The canonical example programs of the Datalog literature."""

    def test_family_and_ancestor(self):
        text = load("01-family.dl")
        engine = run_program(text)
        self.assertEqual(engine.rels["grandparent"],
                         {("abe", "carl"), ("abe", "dana")})
        self.assertEqual(engine.rels["ancestor"], {
            ("abe", "bob"), ("abe", "ann"), ("abe", "carl"),
            ("abe", "dana"), ("bob", "carl"), ("ann", "dana")})
        # the documented lesson-1 bug: everyone is their own sibling
        self.assertIn(("bob", "bob"), engine.rels["sibling"])
        # goal-directed: only bob's descendants are derived (exactly one
        # ancestor#bf fact, against six in the full relation)
        mengine, answers = magic_query(parse(text),
                                       query_atom("ancestor(bob, X)"))
        self.assertEqual(answers, {("bob", "carl")})
        self.assertEqual(len(mengine.rels["ancestor#bf"]), 1)

    def test_same_generation(self):
        # the classic magic-sets benchmark: cal and dee are cousins
        text = load("04-same-generation.dl")
        engine = run_program(text)
        self.assertEqual(
            {t for t in engine.rels["sg"] if t[0] != t[1]},
            {("ann", "bob"), ("bob", "ann"), ("cal", "dee"), ("dee", "cal")})
        _m, answers = magic_query(parse(text), query_atom("sg(cal, Y)"))
        self.assertEqual(answers, {("cal", "cal"), ("cal", "dee")})

    def test_tweety_default_reasoning(self):
        # birds fly unless known to be abnormal; penguins are abnormal
        engine = run_program(load("03-tweety.dl"))
        self.assertEqual(engine.rels["flies"], {("tweety",)})

    def test_barber_paradox(self):
        # the barber shaves exactly those who do not shave themselves
        text = load("03-barber.dl")
        with self.assertRaises(StratificationError):
            run_program(text)
        clauses = parse(text)
        self.assertEqual(stable_models(clauses), [])
        true, undef = well_founded(clauses)
        self.assertEqual(undef, {("shaves", ("barber", "barber"))})
        self.assertIn(("shaves", ("barber", "plato")), true)

    def test_even_odd_mutual_recursion(self):
        engine = run_program(load("02-even-odd.dl"))
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
        engine = run_program(load("02-points-to.dl"))
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
        clauses = parse(load("05-cafe-foodary.dl"))
        _engine, answers = magic_query(clauses, query_atom("eats_in_cafe(X)"))
        self.assertEqual(answers, {("bob",), ("carol",)})

    def test_cafe_paradox_still_rejected_under_magic(self):
        # the negated subgoal pulls in the original cycle untransformed
        clauses = parse(load("05-cafe-paradox.dl"))
        with self.assertRaises(StratificationError):
            magic_query(clauses, query_atom("eats_at_home(alice)"))


class SemanticsTests(unittest.TestCase):
    """Stratifiability is syntactic; these tests check the semantic layer
    (stable models, well-founded model) and that the two are not conflated."""

    def test_unstratifiable_program_can_still_have_stable_models(self):
        # The standard example: unstratifiable, yet two stable models.
        clauses = parse(load("03-win.dl"))
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
        text = load("05-cafe-foodary.dl")
        engine = run_program(text)
        models = stable_models(parse(text))
        self.assertEqual(len(models), 1)
        expected = {(p, t) for p, ts in engine.rels.items() for t in ts}
        self.assertEqual(models[0], expected)


class CafeTests(unittest.TestCase):
    def test_paradox_is_rejected_as_unstratifiable(self):
        with self.assertRaises(StratificationError) as cm:
            run_program(load("05-cafe-paradox.dl"))
        msg = str(cm.exception)
        self.assertIn("eats_in_cafe", msg)
        self.assertIn("household_cooks", msg)
        # the offending cycle is negation through recursion between the two
        preds = {p for edge in cm.exception.cycle for p in edge[:2]}
        self.assertEqual(preds, {"eats_in_cafe", "household_cooks"})

    def test_paradox_has_no_stable_model(self):
        # The semantic verdict behind the syntactic rejection: this
        # particular program really is paradoxical — no stable model.
        self.assertEqual(stable_models(parse(load("05-cafe-paradox.dl"))), [])

    def test_paradox_wfs_leaves_exactly_bobs_atoms_undefined(self):
        true, undef = well_founded(parse(load("05-cafe-paradox.dl")))
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
        engine = run_program(load("05-cafe-constraint.dl"))
        self.assertEqual(engine.rels["household_cooks"],
                         {("house_a",), ("cafe_house",)})
        self.assertEqual(engine.rels["eats_at"], {
            ("alice", "house_a"), ("alan", "house_a"),
            ("bob", "cafe_house"), ("carol", "cafe_house")})
        self.assertEqual(engine.rels["violation"], {("bob",)})

    def test_foodary_model_lets_bob_eat_in_the_cafe(self):
        engine = run_program(load("05-cafe-foodary.dl"))
        self.assertEqual(engine.rels["household_cooks"], {("house_a",)})
        self.assertEqual(engine.rels["eats_at_home"], {("alice",), ("alan",)})
        self.assertEqual(engine.rels["eats_in_cafe"], {("bob",), ("carol",)})
        # the policy's two conclusions hold: no violations derived
        self.assertEqual(engine.rels.get("conclusion1_violated", set()), set())
        self.assertEqual(engine.rels.get("conclusion2_violated", set()), set())


ROUTES = load("06-routes.dl")


class SemiringTests(unittest.TestCase):
    def test_minplus_shortest_paths(self):
        eng = run_semiring(ROUTES, "minplus")
        self.assertEqual(eng.value("path", ("a", "d")), 4)  # a-c-d / a-b-c-d
        self.assertEqual(eng.value("path", ("a", "e")), 7)
        self.assertEqual(eng.value("path", ("b", "d")), 3)  # b-c-d beats b-d

    def test_count_distinct_derivations(self):
        eng = run_semiring(ROUTES, "count")
        self.assertEqual(eng.value("path", ("a", "d")), 3)
        self.assertEqual(eng.value("path", ("a", "e")), 3)
        self.assertEqual(eng.value("path", ("b", "d")), 2)

    def test_why_provenance_minimal_witnesses(self):
        eng = run_semiring(ROUTES, "why")
        witnesses = eng.value("path", ("b", "d"))
        self.assertEqual(witnesses, frozenset([
            frozenset(["edge(b, d)"]),
            frozenset(["edge(b, c)", "edge(c, d)"]),
        ]))

    def test_bool_semiring_matches_core_engine(self):
        eng = run_semiring(ROUTES, "bool")
        core = run_program(ROUTES)
        self.assertEqual(set(eng.rels["path"]), core.rels["path"])

    def test_viterbi_best_derivation(self):
        eng = run_semiring(load("07-prob-reach.dl"), "viterbi")
        # best route s-a-t (0.81) beats s-b-t (0.475) and s-a-b-t (0.684)
        self.assertAlmostEqual(eng.value("reach", ("s", "t")), 0.81)

    def test_duplicate_facts_count_once(self):
        eng = run_semiring(
            "edge(a, b). edge(a, b). path(X, Y) :- edge(X, Y).", "count")
        self.assertEqual(eng.value("path", ("a", "b")), 1)

    def test_negation_rejected(self):
        with self.assertRaises(DatalogError):
            run_semiring("p(a). q(X) :- p(X), not r(X).", "bool")

    def test_counting_cycles_diverges_with_clear_error(self):
        with self.assertRaises(DatalogError):
            run_semiring("""
                edge(a, b). edge(b, a).
                path(X, Y) :- edge(X, Y).
                path(X, Z) :- edge(X, Y), path(Y, Z).
            """, "count", max_rounds=50)

    def test_minplus_converges_on_cycles(self):
        # idempotent semirings are fine with cycles
        eng = run_semiring("""
            edge(a, b) @ 1. edge(b, a) @ 1. edge(b, c) @ 5.
            path(X, Y) :- edge(X, Y).
            path(X, Z) :- edge(X, Y), path(Y, Z).
        """, "minplus")
        self.assertEqual(eng.value("path", ("a", "c")), 6)


class IncrementalTests(unittest.TestCase):
    GRAPH = load("08-dred-graph.dl")

    def recompute(self, inc):
        """Fresh from-scratch evaluation of inc's current base facts."""
        clauses = [c for c in parse(self.GRAPH) if c.body]
        engine = Engine(Program(clauses))
        for pred, tup in inc.base:
            engine.rels[pred].add(tup)
        engine.run()
        return engine.rels

    def test_insert_matches_recompute(self):
        inc = IncrementalEngine(self.GRAPH)
        stats = inc.insert("edge(n5, n6).")
        self.assertEqual(stats["inserted"], 1)
        self.assertEqual(dict(inc.rels), dict(self.recompute(inc)))
        # far fewer facts touched than the whole relation
        self.assertLess(stats["derived"], len(inc.rels["path"]))

    def test_delete_with_alternative_route_rederives(self):
        inc = IncrementalEngine(self.GRAPH)
        stats = inc.delete("edge(n3, n4).")
        # paths reachable via the n2 -> n4 shortcut survive DRed
        self.assertIn(("n2", "n4"), inc.rels["path"])
        self.assertIn(("n1", "n5"), inc.rels["path"])
        self.assertNotIn(("n3", "n4"), inc.rels["path"])
        self.assertGreater(stats["rederived"], 0)
        self.assertEqual(dict(inc.rels), dict(self.recompute(inc)))

    def test_delete_cutting_reachability(self):
        inc = IncrementalEngine(self.GRAPH)
        inc.delete("edge(n4, n5).")
        self.assertEqual({t for t in inc.rels["path"] if t[1] == "n5"},
                         set())
        self.assertEqual(dict(inc.rels), dict(self.recompute(inc)))

    def test_delete_then_reinsert_roundtrips(self):
        inc = IncrementalEngine(self.GRAPH)
        before = {p: set(ts) for p, ts in inc.rels.items()}
        inc.delete("edge(n2, n4).")
        inc.insert("edge(n2, n4).")
        self.assertEqual({p: set(ts) for p, ts in inc.rels.items()}, before)

    def test_only_base_facts_deletable(self):
        inc = IncrementalEngine(self.GRAPH)
        with self.assertRaises(DatalogError):
            inc.delete("path(n1, n3).")

    def test_negation_rejected(self):
        with self.assertRaises(DatalogError):
            IncrementalEngine("p(a). q(X) :- p(X), not r(X).")


class PrologTests(unittest.TestCase):
    PEANO = load("09-peano.pl")

    def query(self, engine, goal, **kw):
        atom = parse(goal + ".")[0].head
        return engine.query(atom, **kw)

    def test_addition_forward(self):
        engine = prolog.load(self.PEANO)
        answers, truncated = self.query(engine,
                                        "add(s(zero), s(s(zero)), X)")
        self.assertFalse(truncated)
        self.assertEqual([str(a["X"]) for a in answers],
                         ["s(s(s(zero)))"])

    def test_addition_backward_enumerates_splits(self):
        engine = prolog.load(self.PEANO)
        answers, _ = self.query(engine, "add(X, Y, s(s(zero)))")
        self.assertEqual(
            {(str(a["X"]), str(a["Y"])) for a in answers},
            {("zero", "s(s(zero))"), ("s(zero)", "s(zero)"),
             ("s(s(zero))", "zero")})

    def test_depth_bound_reported_on_infinite_enumeration(self):
        engine = prolog.load(self.PEANO)
        answers, truncated = self.query(engine, "nat(X)", depth=10,
                                        max_solutions=100)
        self.assertTrue(answers)          # found some naturals
        self.assertTrue(truncated)        # but the search was cut off

    def test_occurs_check(self):
        engine = prolog.load("eq(X, X).")
        answers, truncated = self.query(engine, "eq(Y, s(Y))")
        self.assertEqual(answers, [])
        self.assertFalse(truncated)       # a real failure, not a timeout

    def test_matches_datalog_on_function_free_programs(self):
        text = """
            parent(abe, bob). parent(bob, carl). parent(carl, dee).
            ancestor(X, Y) :- parent(X, Y).
            ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z).
        """
        engine = prolog.load(text)
        answers, _ = self.query(engine, "ancestor(abe, X)",
                                max_solutions=100)
        self.assertEqual({str(a["X"]) for a in answers},
                         {"bob", "carl", "dee"})

    def test_datalog_rejects_function_symbols_with_boundary_error(self):
        with self.assertRaises(SafetyError) as cm:
            run_program(self.PEANO)
        self.assertIn("function symbols", str(cm.exception))
        self.assertIn("prolog.py", str(cm.exception))

    def test_naf_requires_ground_goal(self):
        engine = prolog.load("p(a). q(a). q(b). bad(X) :- not p(X), q(X).")
        with self.assertRaises(DatalogError):
            self.query(engine, "bad(X)")
        # reordered so the positive literal binds X first: sound answer
        engine = prolog.load("p(a). q(a). q(b). ok(X) :- q(X), not p(X).")
        answers, _ = self.query(engine, "ok(X)")
        self.assertEqual({str(a["X"]) for a in answers}, {"b"})

    def test_naf_fails_when_subproof_truncated(self):
        # q is unprovable but its search never terminates; a truncated
        # sub-proof must NOT make `not q` succeed
        engine = prolog.load("q :- q. p :- not q.")
        answers, incomplete = self.query(engine, "p", depth=10)
        self.assertEqual(answers, [])
        self.assertTrue(incomplete)

    def test_solution_cap_reported_and_exact(self):
        engine = prolog.load(self.PEANO)
        answers, incomplete = self.query(engine, "nat(X)", max_solutions=5)
        self.assertEqual(len(answers), 5)
        self.assertTrue(incomplete)
        answers, incomplete = self.query(engine, "nat(X)", max_solutions=0)
        self.assertEqual(answers, [])


class QueryValidationTests(unittest.TestCase):
    def test_magic_query_rejects_structs_and_bad_arity(self):
        clauses = parse(load("02-reachability.dl"))
        with self.assertRaises(DatalogError):
            magic_query(clauses, query_atom("path(s(a), X)"))
        with self.assertRaises(DatalogError):
            magic_query(clauses, query_atom("path(a)"))

    def test_stable_models_with_mixed_constant_types(self):
        models = stable_models(parse("p(1). p(a). q(X) :- p(X), not r(X)."))
        self.assertEqual(len(models), 1)

    def test_float_exponent_round_trip(self):
        clauses = parse("p(0.00000001).")
        self.assertEqual(clauses[0].head.args[0].value, 1e-08)
        parse("q(1e-08).")  # printed exponent forms parse back


class IncrementalValidationTests(unittest.TestCase):
    GRAPH = load("08-dred-graph.dl")

    def test_invalid_facts_rejected(self):
        inc = IncrementalEngine(self.GRAPH)
        for bad in ("edge(a, b, c).",      # arity mismatch
                    "edge(X, n2).",        # not ground
                    "edge(s(a), n2).",     # function symbol
                    "edge(a, b) @ 3."):    # weight
            with self.assertRaises(DatalogError):
                inc.insert(bad)

    def test_emptied_predicate_matches_fresh_recompute(self):
        inc = IncrementalEngine("""
            edge(a, b).
            path(X, Y) :- edge(X, Y).
            path(X, Z) :- edge(X, Y), path(Y, Z).
        """)
        inc.delete("edge(a, b).")
        fresh = Engine(Program([c for c in parse(self.GRAPH) if c.body]))
        fresh.run()
        self.assertEqual(dict(inc.rels), dict(fresh.rels))


class SubsumptionTests(unittest.TestCase):
    ONT = load("10-family-ontology.dl")

    def test_classifier_discovers_subsumptions(self):
        supers = subsumption.load(self.ONT).classify()
        self.assertIn("parent", supers["father"])
        self.assertIn("father", supers["grandfather"])
        self.assertIn("parent", supers["mother"])
        self.assertNotIn("father", supers["mother"])

    def test_direct_subsumers_form_the_hierarchy(self):
        direct = subsumption.load(self.ONT).direct_subsumers()
        self.assertEqual(direct["grandfather"], {"father"})
        self.assertEqual(direct["father"], {"man", "parent"})
        self.assertEqual(direct["person"], set())

    def test_equivalent_definitions_detected(self):
        ont = subsumption.load(self.ONT + """
            define(dad, and(man, some(has_child, person))).
        """)
        self.assertIn(("dad", "father"), ont.equivalences())

    def test_emitted_program_is_plain_datalog(self):
        text = subsumption.load(self.ONT).emit()
        engine = run_program(text)
        self.assertIn(("father", "parent"), engine.rels["subs"])
        self.assertIn(("grandfather", "father"), engine.rels["subs"])

    def test_rejects_rules_and_unknown_statements(self):
        with self.assertRaises(DatalogError):
            subsumption.load("isa(X, Y) :- other(X, Y).")
        with self.assertRaises(DatalogError):
            subsumption.load("frame(man).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
