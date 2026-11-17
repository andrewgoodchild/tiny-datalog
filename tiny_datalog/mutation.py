#!/usr/bin/env python3
"""
mutation.py — mutation testing for rules: would anything notice if
they were wrong?  (Lesson 27; diagnose.py is the lesson's other half.)

diagnose.py asks whether the rules are right, and needs to be told
what right is.  This module tests the telling.  Each **mutant** is the
program with one edit a tired author could make:

* `drop-rule`: a rule deleted;
* `drop-literal`: one condition removed from a body;
* `negate`: a `not` added or removed;
* `swap-args`: two neighbouring arguments exchanged, in a head or a
  body (`depends(Y, X)` for `depends(X, Y)`);
* `comparison`: `<` for `<=`, `=` for `!=`, and so on.

A mutant is **killed** when a test fails on it.  The tests are the
program's own integrity constraints (lesson 17) and an expectations
file (`--expect`; diagnose.py describes the format).  The survivors
are the list to read, and there are three kinds:

* **It changes an answer and nothing notices.**  An expectation is
  missing, and the report lists a few that would kill them all.
* **It changes nothing on these facts.**  The data lacks the awkward
  case, so no expectation could catch it until a fact is added.
* **It changes nothing on any facts.**  In a general-purpose language
  that is the "equivalent mutant" problem, and it is undecidable.  For
  a rule without negation it is lesson 16's containment test, so these
  are proved equivalent and left out of the score.  A dropped literal
  that proves equivalent was redundant all along.

Edits that are not legal programs (an unsafe rule, a negative cycle)
are discarded: the engine would have refused them, which is a test
passing.

CLI
---
    python3 mutation.py programs/lending-checked.dl
    python3 mutation.py programs/lending-checked.dl --expect programs/lending.expect
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import replace

from tiny_datalog.containment import contains
from tiny_datalog.core import (
    aggregate_of, Atom, cli, DatalogError, format_atom, is_comparison,
    Literal, match, parse, read_program)
from tiny_datalog.datalog import Program
from tiny_datalog.diagnose import read_expectations, run

FLIP = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "=": "!=", "!=": "="}


def _swaps(atom):
    """`atom` with each adjacent pair of differing arguments swapped."""
    for k in range(len(atom.args) - 1):
        a = list(atom.args)
        if a[k] != a[k + 1] and not aggregate_of(atom):
            a[k], a[k + 1] = a[k + 1], a[k]
            yield Atom(atom.pred, tuple(a))


def mutants(clauses):
    """Every one-edit neighbour of a program's rules, as (kind, index,
    new rule or None): the rule at `index` is replaced, or dropped.
    Facts and constraints are left alone: they are the data and the
    tests.  Some neighbours are not programs at all (unsafe, or no
    longer stratified); the caller finds that out by building them."""
    for i, rule in enumerate(clauses):
        if not rule.body or rule.constraint:
            continue
        yield "drop-rule", i, None
        for head in _swaps(rule.head):
            yield "swap-args", i, replace(rule, head=head)
        for j, lit in enumerate(rule.body):
            def body(new):
                return replace(rule, body=rule.body[:j] + new
                               + rule.body[j + 1:])
            if len(rule.body) > 1:
                yield "drop-literal", i, body(())
            if is_comparison(lit):
                flipped = Atom(FLIP[lit.atom.pred], lit.atom.args)
                yield "comparison", i, body((Literal(flipped),))
                continue
            yield "negate", i, body((Literal(lit.atom, not lit.negated),))
            for atom in _swaps(lit.atom):
                yield "swap-args", i, body((Literal(atom, lit.negated),))


def fails(engine, true=(), false=()):
    """Does this evaluated program break an expectation, or one of its
    own constraints?"""
    return (any(t not in engine.rels.get(p, ()) for p, t in true)
            or any(match(a.args, t, {}) is not None for a in false
                   for t in engine.rels.get(a.pred, ()))
            or bool(engine._counterexamples()))


def proved_same(clauses, i, new):
    """Is the mutant equivalent on *every* database?  Decidable for
    rules without negation, by lesson 16's homomorphism: a changed rule
    must contain and be contained by the original, and a dropped rule
    must be contained in one that stays.  Comparing one rule with one
    rule is enough even inside a recursive program: two rules that
    agree on every database agree on whatever the rest derives."""
    old = clauses[i]
    try:
        if new is not None:
            return contains(new, old) and contains(old, new)
        return any(contains(other, old) for k, other in enumerate(clauses)
                   if k != i and other.body and not other.constraint
                   and other.head.pred == old.head.pred)
    except DatalogError:
        return False          # negation, comparison, aggregate: no theory


def mutation_test(clauses, true=(), false=()):
    """Run every mutant.  Returns {"killed": n, "stillborn": n,
    "survived": [...], "equivalent": [...]}, the two lists holding
    (kind, old rule, new rule or None, differences).  A survivor's
    differences are the expectations that would have caught it (see
    `differences`): empty when it derives exactly what the original
    does on these facts."""
    base = run(clauses)
    if fails(base, true, false):
        raise DatalogError(
            "the program fails its own expectations or constraints; "
            "mutation testing measures tests the program passes, so "
            "diagnose it first (diagnose.py)")
    out = {"killed": 0, "stillborn": 0, "survived": [], "equivalent": []}
    for kind, i, new in mutants(clauses):
        changed = clauses[:i] + ([new] if new else []) + clauses[i + 1:]
        try:
            engine = run(changed)
        except DatalogError:
            out["stillborn"] += 1       # unsafe, or unstratified
            continue
        if fails(engine, true, false):
            out["killed"] += 1
        elif proved_same(clauses, i, new):
            out["equivalent"].append((kind, clauses[i], new, set()))
        else:
            out["survived"].append(
                (kind, clauses[i], new, differences(base, engine)))
    return out


def differences(base, mutant):
    """Every single expectation that tells a mutant from the original,
    as text: `fact.` for one the mutant loses, `:- fact.` for one it
    gains.  Each is the original's answer written down, so it is a
    regression test, and only as right as the original is."""
    out = set()
    for pred in set(base.rels) | set(mutant.rels):
        ours = base.rels.get(pred, set())
        theirs = mutant.rels.get(pred, set())
        out |= {"%s." % format_atom(pred, t) for t in ours - theirs}
        out |= {":- %s." % format_atom(pred, t) for t in theirs - ours}
    return out


def cover(survivors):
    """A short list of expectations that would kill every survivor
    that changes an answer: [(expectation, mutants it kills)].  Greedy
    set cover: take whichever kills the most of those left, and repeat.
    Ties go to a fact that must hold, then alphabetically."""
    left = [m[3] for m in survivors if m[3]]
    picks = []
    while left:
        counts = Counter(e for diff in left for e in diff)
        best = min(counts, key=lambda e: (-counts[e], e.startswith(":-"), e))
        picks.append((best, counts[best]))
        left = [diff for diff in left if best not in diff]
    return picks


def score(result):
    """Killed, as a percentage of the mutants that could have been:
    proved-equivalent ones are nobody's fault."""
    counted = result["killed"] + len(result["survived"])
    return 100 * result["killed"] // counted if counted else 100


def _print(result, clauses, tests, verbose):
    rules = sum(1 for c in clauses if c.body and not c.constraint)
    constraints = sum(1 for c in clauses if c.constraint)
    silent = [m for m in result["survived"] if not m[3]]
    loud = [m for m in result["survived"] if m[3]]
    print("%d rules, tested by %d constraints and %d expectations"
          % (rules, constraints, tests))
    print("%d mutants: %d killed, %d survived, %d equivalent   (score %d%%)"
          % (result["killed"] + len(result["survived"])
             + len(result["equivalent"]), result["killed"],
             len(result["survived"]), len(result["equivalent"]),
             score(result)))
    if result["stillborn"]:
        print("(%d more edits were not legal programs: unsafe, or "
              "unstratified)" % result["stillborn"])

    def show(items):
        for kind, old, new, _diff in items:
            print("  %-12s  %s" % (kind, old))
            if new is not None:
                print("  %12s  %s" % ("->", new))

    if loud:
        print("%d survived by changing an answer nothing checks.  "
              "Expecting these would kill them:" % len(loud))
        for expectation, n in cover(loud):
            print("  %-40s  %% kills %d" % (expectation, n))
        if verbose:
            show(loud)
    if silent:
        print("%d survived by changing no answer: these facts lack the "
              "case that matters" % len(silent))
        show(silent)
    if result["equivalent"]:
        print("%d equivalent on every database, by containment, so not "
              "counted:" % len(result["equivalent"]))
        show(result["equivalent"])


@cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Mutation-test a rule set against its integrity "
                    "constraints and an expectations file.")
    ap.add_argument("file", help="the program whose tests are in question")
    ap.add_argument("--expect", metavar="FILE",
                    help="expectations: facts that must hold, and "
                         "`:- fact.` for facts that must not")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="list every surviving mutant, not just the "
                         "expectations that would kill them")
    args = ap.parse_args(argv)
    clauses = parse(read_program(args.file))
    true, false = set(), []
    if args.expect:
        true, false = read_expectations(read_program(args.expect),
                                        Program(clauses).arity)
    _print(mutation_test(clauses, true, false), clauses,
           len(true) + len(false), args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
