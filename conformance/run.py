"""Run the datalog-conformance corpus against every tiny-datalog engine.

    pip install datalog-conformance        # Python 3.11+; not a dependency
    python3 conformance/run.py

Each core case is checked twice over: once through datalog-conformance's own runner,
which compares our semi-naive answers with what Souffle / Nemo / Crepe
produced, and then the same program through every other engine in
tiny_datalog.engines.ENGINES that handles it (naive evaluation, magic
sets, tabling), each of which must give the same answer.  An external corpus that agrees with one engine is a
conformance test; one that must also agree across four is a
differential test as well.

Each defeasible theory goes through tiny_datalog.defeasible, under
every policy the case names, and its conclusions must also satisfy the
relations Antoniou, Billington, Governatori & Maher (2001) prove of the
proof theory: +Δ within +∂, −∂ within −Δ, and no literal both + and −.

A case that fails and is not skipped below fails the run.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]

from datalog_conformance.plugin import discover_yaml_tests  # noqa: E402
from datalog_conformance.runner import YamlTestRunner  # noqa: E402

from adapter import (  # noqa: E402
    TinyDatalogDefeasible, TinyDatalogEvaluator, theory_text)
from tiny_datalog.defeasible import Theory  # noqa: E402
from tiny_datalog.core import Atom, Var  # noqa: E402
from tiny_datalog.engines import ENGINES  # noqa: E402

ARITHMETIC = ("arithmetic is the course's deliberate omission "
              "(lessons/14-arithmetic.md)")
NESTED_LOOP = ("10^5 facts: joins are nested loops by design (README, "
               "'Indexes and join planning'), so this runs for hours")

# case name -> why this engine does not run it.  Keep it short: every
# entry is a capability the course chose not to have, never a bug.
SKIP = {
    "subtraction_chains_are_left_associative": ARITHMETIC,
    "souffle_plus_A": ARITHMETIC,
    "crepe_unbound_variable": ARITHMETIC + "; it uses n - 1 and x + y",
}
NESTED_LOOP_FILES = ("souffle_example_lubm", "souffle_example_hmmer")

DELP = ("checked against DePYsible, i.e. DeLP: it ranks arguments by "
        "specificity, which defeasible logic leaves to explicit r1 > r2")
AMBIGUOUS = ("the corpus labels an ambiguous literal 'undecided'; the "
             "2001 proof theory proves it −∂ (lessons/18, ambiguity)")
SKIP_THEORY = {
    "bozzato_example1_bob_exception": DELP,
    "depysible_not_flies_tweety": DELP,
    "depysible_flies_tweety": DELP,
    "depysible_nests_in_trees_tina": DELP,
    "depysible_nests_in_trees_tweety": DELP,
    "goldszmidt_example1_pacifist_conflict": DELP,
    "antoniou_ambiguous_attacker_blocks_only_in_propagating": AMBIGUOUS,
    "antoniou_ambiguity_propagates_to_downstream_rule": AMBIGUOUS,
}


def theory_skip(path, case):
    """Why a defeasible case is out of scope, or None."""
    if case.theory is None or path.parent.name == "closure":
        return ("rational / lexicographic closure (KLM): a different "
                "family of nonmonotonic logics")
    if case.name in SKIP_THEORY:
        return SKIP_THEORY[case.name]
    if case.theory.conflicts:
        return ("declared conflicts between unrelated literals: a SPINdle "
                "extension; defeasible logic's conflicts are p vs ~p")
    if any(path.stem.endswith(f) for f in NESTED_LOOP_FILES):
        return NESTED_LOOP
    bodies = [b for r in case.theory.strict_rules for b in r.body]
    if any(b.startswith(("not ", "!")) for b in bodies):
        return ("lifted from a program with `not`: defeasible logic has "
                "strong negation only, no negation as failure")
    if any(op in " ".join(bodies + [r.head for r in case.theory.strict_rules])
           for op in ("+", "*", " - ")):
        return ARITHMETIC
    return None


def theory_invariants(case):
    """The TOCL 2001 relations between the four tags, per policy."""
    theory = Theory.parse(theory_text(case.theory))
    problems = []
    for policy in ("blocking", "propagating"):
        t = theory.conclusions(policy)
        for name, ok in (("+Δ within +∂", t["+Δ"] <= t["+∂"]),
                         ("−∂ within −Δ", t["−∂"] <= t["−Δ"]),
                         ("+Δ and −Δ disjoint", not t["+Δ"] & t["−Δ"]),
                         ("+∂ and −∂ disjoint", not t["+∂"] & t["−∂"])):
            if not ok:
                problems.append("%s fails under %s" % (name, policy))
    return problems


def all_variable_query(pred, arity):
    return Atom(pred, tuple(Var("X%d" % i) for i in range(arity)))


def cross_check(evaluator, case):
    """Every engine that handles the program must match semi-naive."""
    program = evaluator.program(case.program)
    clauses = program.facts + program.rules
    reference = ENGINES["seminaive"](clauses)
    others = {name: engine(clauses) for name, engine in ENGINES.items()
              if name != "seminaive" and engine.handles(clauses)}
    problems = []
    for pred in case.expect:
        ours = "p_" + pred
        arity = program.arity.get(ours)
        if arity is None:
            continue
        query = all_variable_query(ours, arity)
        want = reference.answers(query)
        for name, engine in others.items():
            if engine.answers(query) != want:
                problems.append("%s disagrees on %s" % (name, pred))
    return problems


def main():
    passed, skipped, failed = 0, [], []
    for path, case in discover_yaml_tests():
        if case.program is None:            # a defeasible theory
            reason = theory_skip(path, case)
        else:
            reason = SKIP.get(case.name)
            if path.stem in NESTED_LOOP_FILES:
                reason = NESTED_LOOP
        if reason:
            skipped.append((case.name, reason))
            continue
        if case.program is None:
            evaluator = TinyDatalogDefeasible()
            check = theory_invariants
        else:
            # read a singleton variable under `not` the way the source
            # engine did (adapter.py's docstring); otherwise, natively
            evaluator = TinyDatalogEvaluator(project_negations=case.source
                                             .startswith(("nemo", "souffle")))
            check = lambda c, e=evaluator: cross_check(e, c)
        runner = YamlTestRunner(evaluator)
        t0 = time.perf_counter()
        try:
            runner.run_test_case(case)
            problems = [] if case.expect_error is not None else check(case)
        except Exception as exc:  # noqa: BLE001 -- report, keep going
            problems = ["%s: %s" % (type(exc).__name__, str(exc)[:300])]
        took = time.perf_counter() - t0
        if problems:
            failed.append((case.name, problems))
            print("FAIL  %5.1fs  %s" % (took, case.name))
            for p in problems:
                print("        " + p)
        else:
            passed += 1
            print("ok    %5.1fs  %s" % (took, case.name))
    print("\n%d passed, %d failed, %d skipped by design"
          % (passed, len(failed), len(skipped)))
    for reason in sorted(set(r for _n, r in skipped)):
        print("  skipped (%d): %s"
              % (sum(1 for _n, r in skipped if r == reason), reason))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
