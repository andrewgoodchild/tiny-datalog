"""Run the datalog-conformance corpus against every tiny-datalog engine.

    pip install datalog-conformance        # Python 3.11+; not a dependency
    python3 conformance/run.py

Each core case (the defeasible ones are out of scope -- see README.md)
is checked twice over: once through datalog-conformance's own runner,
which compares our semi-naive answers with what Souffle / Nemo / Crepe
produced, and then the same program through naive evaluation, magic
sets, and -- for positive programs -- tabling, each of which must give
the same answer.  An external corpus that agrees with one engine is a
conformance test; one that must also agree across four is a
differential test as well.

A case that fails and is not in SKIP below fails the run.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]

from datalog_conformance.plugin import discover_yaml_tests  # noqa: E402
from datalog_conformance.runner import YamlTestRunner  # noqa: E402

from adapter import TinyDatalogEvaluator, corpus_name  # noqa: E402
from tiny_datalog.datalog import Atom, Engine, Var, match_answers  # noqa: E402
from tiny_datalog.magic import magic_query  # noqa: E402
from tiny_datalog.tabling import TabledEngine  # noqa: E402

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


def all_variable_query(pred, arity):
    return Atom(pred, tuple(Var("X%d" % i) for i in range(arity)))


def cross_check(evaluator, case):
    """Naive, magic and tabled evaluation must match semi-naive."""
    program = evaluator.program(case.program)
    reference = Engine(program)
    reference.run()
    naive = Engine(evaluator.program(case.program), naive=True)
    naive.run()
    positive = not any(l.negated for r in program.rules for l in r.body)
    clauses = program.facts + program.rules
    problems = []
    for pred in case.expect:
        ours = "p_" + pred
        arity = program.arity.get(ours)
        if arity is None:
            continue
        want = reference.rels.get(ours, set())
        if naive.rels.get(ours, set()) != want:
            problems.append("naive disagrees on %s" % pred)
        query = all_variable_query(ours, arity)
        _engine, magic = magic_query(clauses, query)
        if set(magic) != set(match_answers(query, want)):
            problems.append("magic sets disagree on %s" % pred)
        if positive:
            tabled = TabledEngine(clauses).query(query)
            if set(tabled) != set(match_answers(query, want)):
                problems.append("tabling disagrees on %s" % pred)
    return problems


def main():
    passed, skipped, failed = 0, [], []
    for path, case in discover_yaml_tests():
        if case.program is None:            # a defeasible theory
            continue
        reason = SKIP.get(case.name)
        if path.stem in NESTED_LOOP_FILES:
            reason = NESTED_LOOP
        if reason:
            skipped.append((case.name, reason))
            continue
        # read a singleton variable under `not` the way the source
        # engine did (adapter.py's docstring); otherwise, natively
        evaluator = TinyDatalogEvaluator(
            project_negations=case.source.startswith(("nemo", "souffle")))
        runner = YamlTestRunner(evaluator)
        t0 = time.perf_counter()
        try:
            runner.run_test_case(case)
            problems = ([] if case.expect_error is not None
                        else cross_check(evaluator, case))
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
