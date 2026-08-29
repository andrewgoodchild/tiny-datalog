#!/usr/bin/env python3
"""
tabling.py — tabled top-down evaluation: the third vertex of the
evaluation triangle.  (Lesson 15, which ends with a tour of this module.)

The course has shown three ways to answer a Datalog query:

* bottom-up semi-naive (datalog.py) — compute everything, look up;
* magic sets (magic.py) — compile the query's demand into the program,
  then run bottom-up;
* SLD resolution (prolog.py) — chase the goal top-down, tuple at a time,
  repeating subgoals and looping on left recursion.

Tabling is top-down done right: every subgoal (a predicate with a
pattern of bound arguments — an adornment *with its values*) gets a
**table** of answers, filled once and shared by every occurrence.  A
subgoal that reaches itself — left recursion, which sends Prolog into
the abyss — simply reads its own table and grows it to fixpoint.

The implementation is the iterative QSQR formulation, chosen because it
is honest and small: each round re-solves every tabled subgoal
top-down, with recursive calls reading current table contents; new
subgoals encountered get empty tables; repeat until no table grows.
Termination is Datalog's usual gift — finitely many call patterns,
finitely many answers.

The punchline to check for yourself: run a bound query here and under
`datalog.py --magic --trace`, and compare this module's *tables* with
the magic predicates' contents.  They are the same sets — magic sets is
tabling performed at compile time, tabling is magic sets performed at
run time.

Positive programs only (tabling under negation is SLG resolution, which
computes the well-founded semantics — XSB's whole claim to fame — and
is beyond this teaching module).

CLI
---
    python3 tabling.py programs/reachability.dl -q 'path(n5, X)'
    python3 tabling.py programs/left-recursive.dl -q 'ancestor(abe, X)'
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from datalog import (Const, DatalogError, _aggregate_of, _match, _sort_key,
                     check_query_atom, format_fact, parse, parse_goal,
                     validate)


class TabledEngine:
    """Iterative QSQR: tables keyed by call pattern, filled to fixpoint.

    After query(), `tables` maps (pred, pattern) — pattern has a constant
    per bound argument and None per free one — to the set of full answer
    tuples for that subgoal, and `rounds` records the outer iterations."""

    def __init__(self, clauses):
        self.arity = validate(clauses)
        for c in clauses:
            if c.retract:
                raise DatalogError("retraction is incremental.py's job: %s" % c)
            if c.body and _aggregate_of(c.head):
                raise DatalogError(
                    "tabled aggregation needs completion detection (real "
                    "SLG); this module is positive-rules-only: %s" % c)
            for lit in c.body:
                if lit.negated:
                    raise DatalogError(
                        "tabling under negation is SLG resolution (the "
                        "well-founded semantics, XSB) — beyond this "
                        "module: %s" % c)
        self.by_pred = defaultdict(list)   # (pred, arity) -> clauses
        for c in clauses:
            self.by_pred[(c.head.pred, len(c.head.args))].append(c)
        self.tables = {}
        self.rounds = 0

    # -- call patterns ------------------------------------------------------

    @staticmethod
    def _pattern(atom, subst):
        """The call pattern of an atom under a substitution: the bound
        arguments' values, None where still free."""
        out = []
        for a in atom.args:
            if isinstance(a, Const):
                out.append(a.value)
            elif a.name in subst:
                out.append(subst[a.name])
            else:
                out.append(None)
        return tuple(out)

    def _table(self, pred, pattern):
        key = (pred, pattern)
        if key not in self.tables:
            self.tables[key] = set()   # discovered a new subgoal
            self._grew = True          # ...which the fixpoint must revisit
        return self.tables[key]

    # -- one round of top-down solving --------------------------------------

    def _prove(self, body, subst):
        """Solve a rule body left to right; recursive calls read the
        current tables (never the clauses directly — that is the whole
        trick: no infinite descent, the fixpoint loop supplies growth)."""
        if not body:
            yield subst
            return
        lit, rest = body[0], body[1:]
        table = self._table(lit.atom.pred, self._pattern(lit.atom, subst))
        for ans in table:
            s = _match(lit.atom.args, ans, subst)
            if s is not None:
                yield from self._prove(rest, s)

    def _answers_for(self, key):
        """Re-derive a subgoal's answers from its clauses, one step of
        head unification plus a tabled body proof."""
        pred, pattern = key
        for clause in self.by_pred.get((pred, len(pattern)), ()):
            # unify the head with the call pattern (bound args only)
            seed = {}
            ok = True
            for a, v in zip(clause.head.args, pattern):
                if v is None:
                    continue
                if isinstance(a, Const):
                    if a.value != v:
                        ok = False
                        break
                elif a.name in seed and seed[a.name] != v:
                    ok = False
                    break
                else:
                    seed[a.name] = v
            if not ok:
                continue
            for s in self._prove(list(clause.body), seed):
                yield tuple(a.value if isinstance(a, Const) else s[a.name]
                            for a in clause.head.args)

    # -- the fixpoint --------------------------------------------------------

    def query(self, atom):
        """All answers to `atom`, computed by tabled top-down evaluation.
        Also populates self.tables / self.rounds for inspection."""
        check_query_atom(atom, self.arity)
        root = (atom.pred, self._pattern(atom, {}))
        self.tables = {root: set()}
        self.rounds = 0
        changed = True
        while changed:
            changed = False
            self._grew = False
            self.rounds += 1
            for key in list(self.tables):
                table = self.tables[key]
                for ans in list(self._answers_for(key)):
                    if ans not in table:
                        table.add(ans)
                        changed = True
            changed = changed or self._grew
        return {t for t in self.tables[root]
                if _match(atom.args, t, {}) is not None}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="tabling.py",
        description="Tabled top-down (QSQR) evaluation of positive "
                    "Datalog — handles left recursion SLD cannot.")
    ap.add_argument("file", help="Datalog program (.dl), positive rules only")
    ap.add_argument("-q", "--query", action="append", default=[],
                    metavar="ATOM", help="goal to solve (repeatable)")
    ap.add_argument("-t", "--tables", action="store_true",
                    help="also print every table (compare these with the "
                         "magic predicates from datalog.py --magic!)")
    args = ap.parse_args(argv)

    with open(args.file) as fh:
        text = fh.read()
    try:
        engine = TabledEngine(parse(text))
    except DatalogError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    for q in args.query:
        try:
            atom = parse_goal(q)
            answers = engine.query(atom)
        except DatalogError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
        print("?- %s   [tabled]" % atom)
        for tup in sorted(answers, key=_sort_key):
            print("   " + format_fact(atom.pred, tup))
        print("   (%d answer%s; %d subgoal table%s, %d rounds)"
              % (len(answers), "" if len(answers) == 1 else "s",
                 len(engine.tables), "" if len(engine.tables) == 1 else "s",
                 engine.rounds))
        if args.tables:
            for (pred, pattern), tbl in sorted(
                    engine.tables.items(),
                    key=lambda kv: (kv[0][0], str(kv[0][1]))):
                shown = ", ".join("_" if v is None else str(v)
                                  for v in pattern)
                print("   table %s(%s): %d answer%s"
                      % (pred, shown, len(tbl),
                         "" if len(tbl) == 1 else "s"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
