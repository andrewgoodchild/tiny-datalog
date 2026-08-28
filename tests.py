#!/usr/bin/env python3
"""Tests for the whole repository: the core engine (parser, safety,
stratification, semi-naive, magic sets, stable/well-founded models), the
classic example programs, and the satellite modules (semiring.py,
incremental.py, prolog.py)."""

import os
import random
import subprocess
import sys
import tempfile
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
import containment
from tabling import TabledEngine
from datalog import match_answers, format_fact, _sort_key, explain


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
        self.assertIn(("win", "win", "not"), cm.exception.cycle)

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
        engine = run_program(load("reachability.dl"))
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

    def test_supply_chain_reachability(self):
        # 292 dependency facts, 12 services, one CVE: which services are
        # exposed is not readable off the data, which is the point
        text = load("supply-chain.dl")
        engine = run_program(text)
        self.assertEqual(
            {s for s, _c in engine.rels["exposed"]},
            {"pkg0", "pkg4", "pkg5", "pkg8"})
        # the derivation is the remediation path
        tree = "\n".join(explain(engine, "exposed",
                                 ("pkg4", "cve_2026_0001")))
        self.assertIn("uses(pkg4, pkg21)", tree)
        self.assertIn("vulnerable(pkg21, cve_2026_0001)   (base fact)", tree)

    def test_supply_chain_new_cve_is_incremental(self):
        # a CVE published overnight must not mean recomputing everything.
        # (That the repair equals a fresh recompute is established for
        # arbitrary programs by DifferentialFuzzTests; here we only need
        # that the incremental path handles this one.)
        inc = IncrementalEngine(load("supply-chain.dl"))
        before = {s for s, _c in inc.rels["exposed"]}
        stats = inc.insert("vulnerable(pkg40, cve_2026_0002).")
        self.assertEqual(stats["inserted"], 1)
        self.assertGreater(stats["derived"], 0)
        after = {s for s, c in inc.rels["exposed"] if c == "cve_2026_0002"}
        self.assertTrue(after > before)

    def test_lending_policy_drafts(self):
        # lesson 16: the engine catches both drafts, in different ways
        with self.assertRaises(SafetyError) as cm:
            run_program("member(iris). may_borrow(P) :- member(P), "
                        "not overdue(P, B).")
        self.assertIn("not overdue(P, B)", str(cm.exception))
        # draft 2 runs but lets a suspended staff member borrow
        draft2 = run_program("""
            member(kim). staff(kim). suspended(kim).
            has_overdue(P) :- overdue(P, _).
            may_borrow(P) :- member(P), not has_overdue(P), not suspended(P).
            may_borrow(P) :- staff(P).
        """)
        self.assertIn(("kim",), draft2.rels["may_borrow"])
        tree = "\n".join(explain(draft2, "may_borrow", ("kim",)))
        self.assertIn("may_borrow(P) :- staff(P).", tree)
        # the shipped draft 3 fixes it
        final = run_program(load("lending.dl"))
        self.assertEqual(final.rels["may_borrow"], {("iris",), ("kim",)})

    def test_eligibility_policy(self):
        # the README's opening example: negation as an exemption, and a
        # derivation tree that names the fact doing the discriminating
        engine = run_program(load("eligibility.dl"))
        self.assertEqual(engine.rels["eligible"],
                         {("bob",), ("cyril",), ("edith",)})
        self.assertNotIn(("dana",), engine.rels["eligible"])  # employed
        self.assertEqual(engine.rels["qualifying_household"],
                         {("oak_house",), ("elm_house",)})
        tree = "\n".join(explain(engine, "eligible", ("bob",)))
        self.assertIn("qualifying_household(oak_house)", tree)
        self.assertIn("receives_pension(cyril)   (base fact)", tree)
        self.assertIn("not employed(bob)", tree)

    def test_eligibility_paradox(self):
        # the README's second demo: one plausible anti-double-dipping
        # clause turns the same policy self-referential
        text = load("eligibility-paradox.dl")
        with self.assertRaises(StratificationError) as cm:
            run_program(text)
        message = str(cm.exception)
        for pred in ("qualifying_household", "claiming", "eligible"):
            self.assertIn(pred, message)
        self.assertEqual(stable_models(parse(text)), [])
        _true, undefined = well_founded(parse(text))
        self.assertEqual(undefined, {
            ("claiming", ("oak_house",)),
            ("qualifying_household", ("oak_house",)),
            ("eligible", ("bob",)),
            ("eligible", ("cyril",)),
        })

    def test_eligibility_stable_and_underspecified(self):
        # the README's three-way verdict: one model, none, or several
        stable = run_program(load("eligibility-stable.dl"))
        self.assertEqual(stable.rels["eligible"], {("bob",), ("cyril",)})
        # elm_house is excluded by the register, not by the rules looping
        self.assertEqual(stable.rels["qualifying_household"],
                         {("oak_house",)})
        # negating only base facts forces no stratum boundary
        self.assertEqual(set(stable.program.strata.values()), {1})

        choice = parse(load("eligibility-choice.dl"))
        with self.assertRaises(StratificationError):
            run_program(load("eligibility-choice.dl"))
        models = stable_models(choice)
        self.assertEqual(len(models), 2)
        claimants = sorted(sorted(a[1][0] for a in m
                                  if a[0] == "eligible") for m in models)
        # the fork is localised: oak_house is contested (bob or cyril),
        # elm_house is settled, so edith claims in both readings
        self.assertEqual(claimants, [["bob", "edith"], ["cyril", "edith"]])
        true, undefined = well_founded(choice)
        self.assertIn(("eligible", ("edith",)), true)
        self.assertEqual({a[1][0] for a in undefined if a[0] == "eligible"},
                         {"bob", "cyril"})

    def test_family_and_ancestor(self):
        text = load("family.dl")
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
        text = load("same-generation.dl")
        engine = run_program(text)
        self.assertEqual(
            {t for t in engine.rels["sg"] if t[0] != t[1]},
            {("ann", "bob"), ("bob", "ann"), ("cal", "dee"), ("dee", "cal")})
        _m, answers = magic_query(parse(text), query_atom("sg(cal, Y)"))
        self.assertEqual(answers, {("cal", "cal"), ("cal", "dee")})

    def test_tweety_default_reasoning(self):
        # birds fly unless known to be abnormal; penguins are abnormal
        engine = run_program(load("tweety.dl"))
        self.assertEqual(engine.rels["flies"], {("tweety",)})

    def test_barber_paradox(self):
        # the barber shaves exactly those who do not shave themselves
        text = load("barber.dl")
        with self.assertRaises(StratificationError):
            run_program(text)
        clauses = parse(text)
        self.assertEqual(stable_models(clauses), [])
        true, undef = well_founded(clauses)
        self.assertEqual(undef, {("shaves", ("barber", "barber"))})
        self.assertIn(("shaves", ("barber", "plato")), true)

    def test_even_odd_mutual_recursion(self):
        engine = run_program(load("even-odd.dl"))
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
        engine = run_program(load("points-to.dl"))
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
        clauses = parse(load("cafe-foodary.dl"))
        _engine, answers = magic_query(clauses, query_atom("eats_in_cafe(X)"))
        self.assertEqual(answers, {("bob",), ("carol",)})

    def test_cafe_paradox_still_rejected_under_magic(self):
        # the negated subgoal pulls in the original cycle untransformed
        clauses = parse(load("cafe-paradox.dl"))
        with self.assertRaises(StratificationError):
            magic_query(clauses, query_atom("eats_at_home(alice)"))


class SemanticsTests(unittest.TestCase):
    """Stratifiability is syntactic; these tests check the semantic layer
    (stable models, well-founded model) and that the two are not conflated."""

    def test_unstratifiable_program_can_still_have_stable_models(self):
        # The standard example: unstratifiable, yet two stable models.
        clauses = parse(load("win.dl"))
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
        text = load("cafe-foodary.dl")
        engine = run_program(text)
        models = stable_models(parse(text))
        self.assertEqual(len(models), 1)
        expected = {(p, t) for p, ts in engine.rels.items() for t in ts}
        self.assertEqual(models[0], expected)


class CafeTests(unittest.TestCase):
    def test_paradox_is_rejected_as_unstratifiable(self):
        with self.assertRaises(StratificationError) as cm:
            run_program(load("cafe-paradox.dl"))
        msg = str(cm.exception)
        self.assertIn("eats_in_cafe", msg)
        self.assertIn("household_cooks", msg)
        # the offending cycle is negation through recursion between the two
        preds = {p for edge in cm.exception.cycle for p in edge[:2]}
        self.assertEqual(preds, {"eats_in_cafe", "household_cooks"})

    def test_paradox_has_no_stable_model(self):
        # The semantic verdict behind the syntactic rejection: this
        # particular program really is paradoxical — no stable model.
        self.assertEqual(stable_models(parse(load("cafe-paradox.dl"))), [])

    def test_paradox_wfs_leaves_exactly_bobs_atoms_undefined(self):
        true, undef = well_founded(parse(load("cafe-paradox.dl")))
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
        engine = run_program(load("cafe-constraint.dl"))
        self.assertEqual(engine.rels["household_cooks"],
                         {("house_a",), ("cafe_house",)})
        self.assertEqual(engine.rels["eats_at"], {
            ("alice", "house_a"), ("alan", "house_a"),
            ("bob", "cafe_house"), ("carol", "cafe_house")})
        self.assertEqual(engine.rels["violation"], {("bob",)})

    def test_foodary_model_lets_bob_eat_in_the_cafe(self):
        engine = run_program(load("cafe-foodary.dl"))
        self.assertEqual(engine.rels["household_cooks"], {("house_a",)})
        self.assertEqual(engine.rels["eats_at_home"], {("alice",), ("alan",)})
        self.assertEqual(engine.rels["eats_in_cafe"], {("bob",), ("carol",)})
        # the policy's two conclusions hold: no violations derived
        self.assertEqual(engine.rels.get("conclusion1_violated", set()), set())
        self.assertEqual(engine.rels.get("conclusion2_violated", set()), set())


ROUTES = load("routes.dl")


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
        eng = run_semiring(load("prob-reach.dl"), "viterbi")
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
    GRAPH = load("dred-graph.dl")

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

    def test_bf_delete_matches_dred_and_recompute(self):
        # same affected set, same survivors, opposite work profile
        dred = IncrementalEngine(self.GRAPH)
        d = dred.delete("edge(n3, n4).")
        bf = IncrementalEngine(self.GRAPH)
        b = bf.delete("edge(n3, n4).", strategy="bf")
        self.assertEqual(dict(bf.rels), dict(dred.rels))
        self.assertEqual(dict(bf.rels), dict(self.recompute(bf)))
        self.assertEqual(b["affected"], d["over_deleted"])
        self.assertEqual(b["confirmed"], d["rederived"])
        self.assertEqual(b["removed"], d["net_removed"])
        # deterministic search order, so the work counter is stable
        self.assertEqual(b["backward_checks"], 8)

    def test_bf_support_must_be_well_founded(self):
        # a cycle must not keep itself alive: after edge(c, a) goes, the
        # paths around the a-b-c loop have no acyclic support left, even
        # though each still "derives" from another doomed path fact
        cyc = ("edge(a, b). edge(b, c). edge(c, a). edge(a, d).\n"
               "path(X, Y) :- edge(X, Y).\n"
               "path(X, Z) :- edge(X, Y), path(Y, Z).\n")
        bf = IncrementalEngine(cyc)
        stats = bf.delete("edge(c, a).", strategy="bf")
        self.assertEqual(stats["removed"], 9)
        fresh = run_program(cyc.replace("edge(c, a). ", ""))
        self.assertEqual({p: s for p, s in bf.rels.items() if s},
                         {p: s for p, s in fresh.rels.items() if s})

    def test_bf_disturbs_only_what_died(self):
        # lesson 9's headline: deleting the README's remediation edge
        # affects 112 facts and kills exactly one — the edge itself.
        # Every derived fact survives (pkg4 reaches pkg13 via pkg8), so
        # uses(pkg4, pkg13) is still true and pkg4 is still exposed:
        # the fix from the --explain tree changed nothing at all.
        inc = IncrementalEngine(load("supply-chain.dl"))
        stats = inc.delete("depends(pkg4, pkg13).", strategy="bf")
        self.assertEqual(stats["affected"], 112)
        self.assertEqual(stats["confirmed"], 111)
        self.assertEqual(stats["removed"], 1)
        self.assertNotIn(("pkg4", "pkg13"), inc.rels["depends"])
        self.assertIn(("pkg4", "pkg13"), inc.rels["uses"])
        self.assertIn(("pkg4", "cve_2026_0001"), inc.rels["exposed"])

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
    PEANO = load("peano.pl")

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


class ClosedAndOpenWorldTests(unittest.TestCase):
    """Lesson 4: the two engines disagree about what absence means, and
    the disagreement is observable."""

    def test_missing_data_produces_a_confident_wrong_answer(self):
        engine = run_program(load("missing-data.dl"))
        # dana has no employment record at all
        self.assertIn(("dana",), engine.rels["eligible_naive"])
        self.assertNotIn(("dana",), engine.rels["eligible"])
        self.assertEqual(engine.rels["pending"], {("dana",)})
        self.assertEqual(engine.rels["eligible"], {("bob",)})
        # and the wrong answer comes with a full derivation
        tree = "\n".join(explain(engine, "eligible_naive", ("dana",)))
        self.assertIn("not employed(dana)", tree)

    def test_closed_world_is_non_monotone(self):
        base = load("tweety.dl")
        self.assertEqual(run_program(base).rels["flies"], {("tweety",)})
        # adding a fact REMOVES a conclusion
        self.assertEqual(
            run_program(base + "\npenguin(tweety).").rels.get("flies", set()),
            set())

    def test_open_world_is_monotone(self):
        base = load("family-ontology.dl")
        before = subsumption.load(base).classify()["father"]
        after = subsumption.load(base + "\nisa(father, taxpayer).\n"
                                 ).classify()["father"]
        # adding an axiom only ever ADDS subsumers
        self.assertTrue(before < after)
        self.assertIn("taxpayer", after - before)


class QueryValidationTests(unittest.TestCase):
    def test_magic_query_rejects_structs_and_bad_arity(self):
        clauses = parse(load("reachability.dl"))
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
    GRAPH = load("dred-graph.dl")

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


class AggregationTests(unittest.TestCase):
    SPEND = """
        charge(alice, groceries, 120).  charge(alice, transport, 60).
        charge(bob, groceries, 90).     charge(bob, rent, 900).
        total(P, sum(A))    :- charge(P, C, A).
        howmany(P, count(C)) :- charge(P, C, A).
        cheapest(P, min(A)) :- charge(P, C, A).
        biggest(P, max(A))  :- charge(P, C, A).
    """

    def test_group_and_fold(self):
        engine = run_program(self.SPEND)
        self.assertEqual(engine.rels["total"],
                         {("alice", 180), ("bob", 990)})
        self.assertEqual(engine.rels["howmany"],
                         {("alice", 2), ("bob", 2)})
        self.assertEqual(engine.rels["cheapest"],
                         {("alice", 60), ("bob", 90)})
        self.assertEqual(engine.rels["biggest"],
                         {("alice", 120), ("bob", 900)})

    def test_aggregation_over_recursion_stratifies(self):
        engine = run_program(load("reachability.dl") + """
            reach_count(X, count(Y)) :- path(X, Y).
        """)
        self.assertIn(("n1", 9), engine.rels["reach_count"])
        strata = engine.program.strata
        self.assertLess(strata["path"], strata["reach_count"])

    def test_aggregate_cycle_rejected_as_aggregation(self):
        with self.assertRaises(StratificationError) as cm:
            run_program("p(a, 1). q(count(X)) :- q(Y), p(X, N).")
        self.assertIn("aggregation", str(cm.exception))

    def test_aggregates_range_over_solutions_not_values(self):
        # SQL semantics: two DIFFERENT charges of 50 both count (rows are
        # distinct solutions), and count is independent of which bound
        # variable is named
        engine = run_program("""
            charge(alice, a, 50).  charge(alice, b, 50).
            spent(P, sum(A)) :- charge(P, C, A).
            rows_c(P, count(C)) :- charge(P, C, A).
            rows_a(P, count(A)) :- charge(P, C, A).
        """)
        self.assertEqual(engine.rels["spent"], {("alice", 100)})
        self.assertEqual(engine.rels["rows_c"], engine.rels["rows_a"])

    def test_identical_solutions_still_count_once(self):
        # the same solution reached through two rule paths is one row
        engine = run_program("""
            charge(alice, a, 50).
            pay(P, C, A) :- charge(P, C, A).
            pay(P, C, A) :- charge(P, C, A), charge(P, C, A).
            spent(P, sum(A)) :- pay(P, C, A).
        """)
        self.assertEqual(engine.rels["spent"], {("alice", 50)})

    def test_sum_over_non_numeric_rejected(self):
        with self.assertRaises(DatalogError):
            run_program("q(alice, home). t(P, sum(W)) :- q(P, W).")

    def test_magic_falls_back_to_full_for_aggregates(self):
        clauses = parse(self.SPEND)
        _e, answers = magic_query(clauses, query_atom("total(alice, X)"))
        self.assertEqual(answers, {("alice", 180)})

    def test_aggregate_fact_and_double_aggregate_rejected(self):
        with self.assertRaises(SafetyError):
            run_program("t(sum(X)).")
        with self.assertRaises(SafetyError):
            run_program("q(a, 1). t(sum(X), count(Y)) :- q(X, Y).")


class NaiveAndExplainTests(unittest.TestCase):
    def test_naive_matches_seminaive(self):
        text = load("reachability.dl")
        fast = run_program(text)
        slow = Engine(Program(parse(text)), naive=True)
        slow.run()
        self.assertEqual(dict(fast.rels), dict(slow.rels))
        # naive rederives: total tuples produced far exceeds the relation
        produced = sum(slow.stats[0]["produced"])
        self.assertGreater(produced, len(slow.rels["path"]))

    def test_explain_builds_wellfounded_tree(self):
        engine = run_program(load("reachability.dl"))
        lines = explain(engine, "path", ("n1", "n3"))
        self.assertIn("(base fact)", "\n".join(lines))
        self.assertIn("[via", lines[0])
        # the fact never justifies itself
        self.assertEqual(
            sum(1 for l in lines if l.strip().startswith("path(n1, n3)")), 1)

    def test_explain_aggregate_shows_group(self):
        engine = run_program(AggregationTests.SPEND)
        lines = explain(engine, "total", ("alice", 180))
        self.assertIn("sum over 2 body solutions", "\n".join(lines))


class RetractionTests(unittest.TestCase):
    def test_core_engine_rejects_retraction(self):
        with self.assertRaises(SafetyError) as cm:
            run_program("edge(a, b)~.")
        self.assertIn("incremental.py", str(cm.exception))

    def test_apply_mixed_update_script(self):
        inc = IncrementalEngine(load("dred-graph.dl"))
        stats = inc.apply("edge(n3, n4)~.  edge(n2, n9).")
        self.assertEqual(stats["deleted"], 1)
        self.assertEqual(stats["inserted"], 1)
        self.assertIn(("n1", "n9"), inc.rels["path"])
        self.assertNotIn(("n3", "n4"), inc.rels["path"])

    def test_insert_refuses_retractions(self):
        inc = IncrementalEngine(load("dred-graph.dl"))
        with self.assertRaises(DatalogError):
            inc.insert("edge(a, b)~.")

    def test_retraction_round_trips_through_str(self):
        clause = parse("edge(a, b)~.")[0]
        self.assertTrue(clause.retract)
        self.assertEqual(str(clause), "edge(a, b)~.")


class TablingTests(unittest.TestCase):
    def test_left_recursion_terminates(self):
        engine = TabledEngine(parse(load("left-recursive.dl")))
        answers = engine.query(query_atom("ancestor(abe, X)"))
        self.assertEqual({a[1] for a in answers},
                         {"ann", "bob", "carl", "dee"})

    def test_bound_query_tables_are_the_magic_set(self):
        engine = TabledEngine(parse(load("reachability.dl")))
        engine.query(query_atom("path(n5, X)"))
        path_tables = {key[1][0] for key in engine.tables
                       if key[0] == "path"}
        # only subgoals reachable from n5 — never n1..n4 or the n9 branch
        self.assertEqual(path_tables, {"n5", "n6", "n7", "n8"})

    def test_rejects_negation(self):
        with self.assertRaises(DatalogError):
            TabledEngine(parse(load("tweety.dl")))


class ConformanceTests(unittest.TestCase):
    """One semantics, many algorithms: every applicable strategy must
    return identical answers.  (AbcDatalog's shared-suite pattern.)"""

    CASES = [
        ("ancestor", load("family.dl"), "ancestor(abe, X)"),
        ("reachability", load("reachability.dl"), "path(n5, X)"),
        ("same-generation", load("same-generation.dl"), "sg(cal, Y)"),
        ("even-odd", load("even-odd.dl"), "even(n1, X)"),
        ("tweety", load("tweety.dl"), "flies(X)"),   # negation: no tabling
    ]

    def test_all_strategies_agree(self):
        for name, text, q in self.CASES:
            atom = query_atom(q)
            clauses = parse(text)
            reference = set(match_answers(
                atom, run_program(text).rels.get(atom.pred, ())))
            with self.subTest(case=name, engine="naive"):
                eng = Engine(Program(parse(text)), naive=True)
                eng.run()
                self.assertEqual(
                    set(match_answers(atom, eng.rels.get(atom.pred, ()))),
                    reference)
            with self.subTest(case=name, engine="magic"):
                _e, answers = magic_query(clauses, atom)
                self.assertEqual(answers, reference)
            if not any(l.negated for c in clauses for l in c.body):
                with self.subTest(case=name, engine="tabled"):
                    self.assertEqual(
                        TabledEngine(parse(text)).query(atom), reference)


class ContainmentTests(unittest.TestCase):
    """Chandra–Merlin containment and minimisation (lesson 15)."""

    @staticmethod
    def rule(text):
        return containment._parse_query_rule(text)

    def test_containment_direction(self):
        broad = self.rule("q(X) :- e(X, Y).")
        narrow = self.rule("q(X) :- e(X, Y), e(Y, Z).")
        self.assertTrue(containment.contains(broad, narrow))
        self.assertFalse(containment.contains(narrow, broad))

    def test_head_variables_are_pinned(self):
        # the 2-cycle is NOT equivalent to a single edge; without fixing
        # head variables the homomorphism would wrongly exist
        cycle = self.rule("q(X) :- e(X, Y), e(Y, X).")
        single = self.rule("q(X) :- e(X, Y).")
        self.assertTrue(containment.contains(single, cycle))
        self.assertFalse(containment.contains(cycle, single))
        self.assertEqual(len(containment.minimise(cycle)), 2)

    def test_minimisation_of_shipped_examples(self):
        clauses = parse(load("minimise.dl"))
        by_head = {c.head.pred: c for c in clauses if c.body}
        self.assertEqual(len(containment.minimise(by_head["has_edge"])), 1)
        self.assertEqual(len(containment.minimise(by_head["two_hop"])), 2)
        self.assertEqual(len(containment.minimise(by_head["mutual"])), 2)
        self.assertEqual(len(containment.minimise(by_head["triangle"])), 3)

    def test_minimisation_preserves_answers_on_real_data(self):
        # the theorem says "on every database"; check one of them
        facts = "e(a, b).  e(b, c).  e(c, a).  e(a, d)."
        original = "h(X, Y) :- e(X, Y), e(X, Z)."
        rule = self.rule(original)
        reduced = containment.minimise(rule)
        minimised = "h(%s) :- %s." % (
            ", ".join(str(a) for a in rule.head.args),
            ", ".join(str(a) for a in reduced))
        self.assertEqual(run_program(facts + original).rels["h"],
                         run_program(facts + minimised).rels["h"])

    def test_negation_refused(self):
        with self.assertRaises(DatalogError):
            containment.minimise(self.rule("q(X) :- e(X, Y), not e(Y, X)."))

    def test_shipped_programs_are_already_minimal(self):
        for name in ("family.dl", "same-generation.dl",
                     "reachability.dl"):
            for clause in parse(load(name)):
                if clause.body and not any(l.negated for l in clause.body):
                    with self.subTest(program=name, rule=str(clause)):
                        self.assertEqual(len(containment.minimise(clause)),
                                         len(clause.body))


class SemiringHomomorphismTests(unittest.TestCase):
    """Lesson 7: when may provenance be specialised after the fact?"""

    def test_why_to_minplus_is_a_homomorphism(self):
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "exercises",
                                          "07-homomorphism.py")],
            capture_output=True, text=True, cwd=HERE)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("agrees on every fact", r.stdout)

    def test_why_cannot_determine_count(self):
        text = load("two-derivations.dl")
        why = run_semiring(text, "why")
        count = run_semiring(text, "count")
        # identical provenance, different derivation counts: no function
        # of the why-value can be right about both
        self.assertEqual(why.value("p", ("a", "c")),
                         why.value("q", ("a", "c")))
        self.assertEqual(count.value("p", ("a", "c")), 1)
        self.assertEqual(count.value("q", ("a", "c")), 2)


class DifferentialFuzzTests(unittest.TestCase):
    """Randomised differential testing: generate stratified programs by
    construction, then demand that every applicable strategy agrees.

    The conformance suite pins five hand-written cases; this pins the
    *property* they were sampling.  Seeded, so a failure is replayable;
    the iteration count is CI-sized by default and raisable for a real
    soak:

        TINY_DATALOG_FUZZ=3000 python3 tests.py DifferentialFuzzTests
    """

    DOMAIN = ["a", "b", "c", "d"]
    VARS = ["X", "Y", "Z"]
    EDB = [("p", 2), ("q", 2), ("r", 1)]

    @staticmethod
    def iterations(default):
        return int(os.environ.get("TINY_DATALOG_FUZZ", default))

    def _facts(self, rng):
        out = []
        for name, arity in self.EDB:
            for _ in range(rng.randint(0, 5)):
                args = [rng.choice(self.DOMAIN) for _ in range(arity)]
                out.append("%s(%s)." % (name, ", ".join(args)))
        return out

    def _rule(self, rng, head, arity, positive_pool, negative_pool):
        """A safe rule: head and negated variables are always bound by a
        positive literal, which is what validate() demands."""
        body, bound = [], []
        for _ in range(rng.randint(1, 2)):
            name, ar = rng.choice(positive_pool)
            args = []
            for _ in range(ar):
                if rng.random() < 0.15:
                    args.append(rng.choice(self.DOMAIN))
                else:
                    v = rng.choice(self.VARS)
                    args.append(v)
                    bound.append(v)
            body.append("%s(%s)" % (name, ", ".join(args)))
        bound = sorted(set(bound))
        if negative_pool and bound and rng.random() < 0.4:
            name, ar = rng.choice(negative_pool)
            args = [rng.choice(bound) for _ in range(ar)]
            body.append("not %s(%s)" % (name, ", ".join(args)))
        head_args = [rng.choice(bound) if bound and rng.random() < 0.8
                     else rng.choice(self.DOMAIN) for _ in range(arity)]
        return "%s(%s) :- %s." % (head, ", ".join(head_args),
                                  ", ".join(body))

    def _program(self, rng, negation=True):
        """Stratified by construction: negation only ever points at a
        strictly lower stratum, recursion only within one."""
        s1 = [("s1", rng.choice([1, 2]))]
        s2 = [("t1", rng.choice([1, 2]))]
        rules = []
        for name, arity in s1:
            for _ in range(rng.randint(1, 2)):
                rules.append(self._rule(rng, name, arity, self.EDB + s1,
                                        self.EDB if negation else []))
        for name, arity in s2:
            for _ in range(rng.randint(1, 2)):
                rules.append(self._rule(
                    rng, name, arity, self.EDB + s1 + s2,
                    (self.EDB + s1) if negation else []))
        return "\n".join(self._facts(rng) + rules), s1 + s2

    def _query(self, rng, idb):
        name, arity = rng.choice(idb)
        args = [rng.choice(self.DOMAIN) if rng.random() < 0.5 else "X%d" % i
                for i in range(arity)]
        return query_atom("%s(%s)" % (name, ", ".join(args)))

    def test_all_strategies_agree_on_random_programs(self):
        rng = random.Random(20260823)
        for i in range(self.iterations(400)):
            negation = rng.random() < 0.6
            text, idb = self._program(rng, negation)
            atom = self._query(rng, idb)
            with self.subTest(iteration=i, program=text, query=str(atom)):
                reference = run_program(text)
                ref_answers = set(match_answers(
                    atom, reference.rels.get(atom.pred, ())))

                naive = Engine(Program(parse(text)), naive=True)
                naive.run()
                self.assertEqual(
                    {p: set(ts) for p, ts in naive.rels.items() if ts},
                    {p: set(ts) for p, ts in reference.rels.items() if ts})

                _m, magic_answers = magic_query(parse(text), atom)
                self.assertEqual(magic_answers, ref_answers)

                if not negation:
                    self.assertEqual(
                        TabledEngine(parse(text)).query(atom), ref_answers)

    def test_incremental_matches_recompute_under_random_updates(self):
        rng = random.Random(20260824)
        for i in range(self.iterations(40)):
            text, _idb = self._program(rng, negation=False)
            clauses = parse(text)
            rules = [c for c in clauses if c.body]
            base = {(c.head.pred, tuple(a.value for a in c.head.args))
                    for c in clauses if not c.body}
            inc = IncrementalEngine(text)
            bf = IncrementalEngine(text)
            for step in range(rng.randint(3, 10)):
                name, arity = rng.choice(self.EDB)
                tup = tuple(rng.choice(self.DOMAIN) for _ in range(arity))
                fact = format_fact(name, tup)
                deleting = (name, tup) in base and rng.random() < 0.5
                with self.subTest(iteration=i, step=step, program=text,
                                  op=("delete" if deleting else "insert"),
                                  fact=fact):
                    if deleting:
                        inc.delete(fact)
                        bf.delete(fact, strategy="bf")
                        base.discard((name, tup))
                    else:
                        inc.insert(fact)
                        bf.insert(fact)
                        base.add((name, tup))
                    fresh = Engine(Program(list(rules)))
                    for pred, t in base:
                        fresh.rels[pred].add(t)
                    fresh.run()
                    reference = {p: set(ts)
                                 for p, ts in fresh.rels.items() if ts}
                    self.assertEqual(
                        {p: set(ts) for p, ts in inc.rels.items() if ts},
                        reference)
                    self.assertEqual(
                        {p: set(ts) for p, ts in bf.rels.items() if ts},
                        reference)


class GoldenFileTests(unittest.TestCase):
    """cases/<name>/{program.dl, queries, expected} — add a test without
    writing Python (see cases/README.md)."""

    def test_golden_cases(self):
        case_root = os.path.join(HERE, "cases")
        names = sorted(d for d in os.listdir(case_root)
                       if os.path.isdir(os.path.join(case_root, d)))
        self.assertTrue(names, "no golden cases found")
        for name in names:
            with self.subTest(case=name):
                base = os.path.join(case_root, name)
                with open(os.path.join(base, "program.dl")) as fh:
                    engine = run_program(fh.read())
                lines = []
                with open(os.path.join(base, "queries")) as fh:
                    for q in fh:
                        q = q.strip()
                        if not q or q.startswith("%"):
                            continue
                        atom = query_atom(q.rstrip("."))
                        for tup in sorted(
                                match_answers(atom,
                                              engine.rels.get(atom.pred, ())),
                                key=_sort_key):
                            lines.append(format_fact(atom.pred, tup))
                with open(os.path.join(base, "expected")) as fh:
                    expected = [l for l in fh.read().splitlines() if l]
                self.assertEqual(lines, expected)


class RepositoryClaimTests(unittest.TestCase):
    """Claims the README makes about the repository itself, so they
    cannot rot silently."""

    SATELLITES = ["magic.py", "semantics.py", "semiring.py",
                  "incremental.py", "prolog.py", "tabling.py",
                  "subsumption.py", "containment.py"]

    def test_no_satellite_module_exceeds_400_lines(self):
        for name in self.SATELLITES:
            with self.subTest(module=name):
                with open(os.path.join(HERE, name)) as fh:
                    self.assertLessEqual(len(fh.read().splitlines()), 400)

    def test_incremental_reports_its_own_timing(self):
        # the README quotes a repair time; the tool must actually print
        # one, or the claim is unverifiable from the shell
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "incremental.py"),
             "programs/supply-chain.dl",
             "-u", "vulnerable(pkg100, cve_2026_0002)."],
            capture_output=True, text=True, cwd=HERE)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("'inserted': 1, 'derived': 12", r.stdout)
        self.assertRegex(r.stdout, r"in \d+\.\d+s")
        self.assertIn("from-scratch rebuild", r.stdout)


class ExerciseTests(unittest.TestCase):
    """Every runnable exercise answer, executed — so exercises/ cannot
    rot.  Numbers asserted here are the numbers quoted in the answer
    files."""

    @staticmethod
    def ex(name):
        with open(os.path.join(HERE, "exercises", name)) as fh:
            return fh.read()

    def test_lesson1_cousins_and_aunts(self):
        engine = run_program(self.ex("01-answers.dl"))
        self.assertIn(("carl", "dana"), engine.rels["cousin"])   # real cousins
        self.assertIn(("carl", "carl"), engine.rels["cousin"])   # the documented bug
        self.assertIn(("ann", "carl"), engine.rels["aunt_or_uncle"])
        self.assertIn(("bob", "carl"), engine.rels["aunt_or_uncle"])  # ditto

    def test_lesson2_component_and_bom(self):
        engine = run_program(self.ex("02-answers.dl"))
        self.assertIn(("a", "c"), engine.rels["same_component"])
        self.assertNotIn(("a", "d"), engine.rels["same_component"])
        self.assertEqual(len(engine.rels["has_part"]), 15)
        rounds_with_parts = [r for r in engine.stats[0]["iterations"]
                             if "has_part" in r]
        self.assertEqual(len(rounds_with_parts), 5)

    def test_lesson2_chain16_round_counts(self):
        edges = "".join("edge(n%d, n%d)." % (i, i + 1) for i in range(1, 16))
        base = "path(X, Y) :- edge(X, Y)."
        linear = run_program(edges + base
                             + "path(X, Z) :- edge(X, Y), path(Y, Z).")
        nonlin = run_program(edges + base
                             + "path(X, Z) :- path(X, Y), path(Y, Z).")
        self.assertEqual(len(linear.stats[0]["iterations"]), 16)
        self.assertEqual(len(nonlin.stats[0]["iterations"]), 6)

    def test_lesson3_childless_and_cycles(self):
        engine = run_program(self.ex("03-answers.dl"))
        self.assertEqual(engine.rels["has_no_children"],
                         {("carl",), ("dana",)})
        self.assertEqual(engine.rels["off_cycle"], {("d",)})
        self.assertEqual(max(engine.program.strata.values()), 2)

    def test_lesson4_magic_counts(self):
        clauses = parse(load("family.dl"))
        full = run_program(load("family.dl"))
        full_total = sum(len(full.rels[p]) for p in full.program.idb)
        m, _a = magic_query(clauses, query_atom("ancestor(abe, X)"))
        m_total = sum(len(m.rels.get(p, ())) for p in m.program.idb)
        self.assertEqual((m_total, full_total), (11, 14))

    def test_lesson5_win_chain_unique_model(self):
        models = stable_models(parse(
            "move(a,b). move(b,c). move(c,d). "
            "win(X) :- move(X, Y), not win(Y)."))
        self.assertEqual(len(models), 1)
        self.assertEqual({a for a in models[0] if a[0] == "win"},
                         {("win", ("a",)), ("win", ("c",))})

    def test_lesson6_modified_routes(self):
        text = self.ex("07-answers.dl")
        self.assertEqual(
            run_semiring(text, "minplus").value("path", ("a", "e")), 6)
        self.assertEqual(
            run_semiring(text, "count").value("path", ("a", "e")), 4)
        self.assertEqual(
            len(run_semiring(text, "why").value("path", ("a", "e"))), 4)

    def test_lesson7_exact_probability_script(self):
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "exercises",
                                          "08-exact-prob.py")],
            capture_output=True, text=True, cwd=HERE)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0.934450", r.stdout)
        self.assertIn("exact >= Viterbi: True", r.stdout)

    def test_lesson8_diamond_overdelete(self):
        inc = IncrementalEngine(self.ex("09-answers.dl"))
        stats = inc.delete("edge(s, m1).")
        self.assertEqual((stats["over_deleted"], stats["rederived"],
                          stats["net_removed"]), (6, 4, 2))

    def test_lesson9_mult_and_finite_failure(self):
        engine = prolog.load(load("peano.pl"))
        answers, _ = engine.query(
            query_atom("mult(s(s(zero)), s(s(zero)), X)"), max_solutions=1)
        self.assertEqual(str(answers[0]["X"]), "s(s(s(s(zero))))")
        answers, _ = engine.query(
            query_atom("mult(X, s(s(zero)), s(s(s(s(zero)))))"),
            max_solutions=1)
        self.assertEqual(str(answers[0]["X"]), "s(s(zero))")
        answers, incomplete = engine.query(query_atom("lt(X, zero)"))
        self.assertEqual(answers, [])
        self.assertFalse(incomplete)   # finite failure, not a timeout

    def test_lesson10_grandmother_and_dad(self):
        ont = subsumption.load(self.ex("11-answers.dl"))
        self.assertEqual(ont.direct_subsumers()["grandmother"], {"mother"})
        self.assertIn(("dad", "father"), ont.equivalences())

    def test_lesson11_magic_bob_counts(self):
        m, _a = magic_query(parse(load("family.dl")),
                            query_atom("ancestor(bob, X)"))
        total = sum(len(m.rels.get(p, ())) for p in m.program.idb)
        self.assertEqual(total, 3)   # 2 magic facts + 1 answer fact
        self.assertEqual(m.rels["magic#ancestor#bf"], {("bob",), ("carl",)})

    def test_lesson12_average_parts(self):
        engine = run_program(self.ex("13-answers.dl"))
        self.assertEqual(engine.rels["average_parts"],
                         {("alice", 180, 2), ("bob", 990, 2)})

    def test_lesson13_duality(self):
        te = TabledEngine(parse(load("family.dl")))
        te.query(query_atom("ancestor(bob, X)"))
        table_patterns = {key[1][0] for key in te.tables
                          if key[0] == "ancestor"}
        m, _a = magic_query(parse(load("family.dl")),
                            query_atom("ancestor(bob, X)"))
        magic_starts = {t[0] for t in m.rels["magic#ancestor#bf"]}
        self.assertEqual(table_patterns, magic_starts)


class CLITests(unittest.TestCase):
    """Run datalog.py as a real subprocess.  The script-vs-import module
    duality is where the double-import trap lives (datalog.py aliases
    itself into sys.modules to prevent it); these tests pin the fix."""

    @staticmethod
    def cli(*args):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "datalog.py")] + list(args),
            capture_output=True, text=True, cwd=HERE)

    def test_magic_cli_specialises_bound_queries(self):
        r = self.cli("--magic", "--trace", "-q", "ancestor(abe, X)",
                     "programs/family.dl")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ancestor#bf", r.stdout)
        self.assertNotIn("ancestor#ff", r.stdout)

    def test_models_cli_with_constants_in_rule_bodies(self):
        # a constant inside a rule body crosses the module boundary in
        # _match; under the double-import bug this crashed
        with tempfile.NamedTemporaryFile(
                "w", suffix=".dl", delete=False) as fh:
            fh.write("p(a). p(b). q(X) :- p(X), p(a), not r(X).")
            path = fh.name
        try:
            r = self.cli("--models", path)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Stable models: 1", r.stdout)
        finally:
            os.unlink(path)


class SubsumptionTests(unittest.TestCase):
    ONT = load("family-ontology.dl")

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
