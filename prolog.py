#!/usr/bin/env python3
"""
prolog.py — a miniature top-down Horn-clause interpreter: the other side
of the Datalog boundary.

Datalog is Horn-clause logic with function symbols confiscated; that ban
is what makes bottom-up evaluation terminate.  This module puts the
function symbols back — `s(N)`, `cons(H, T)` — and pays the price:
top-down SLD resolution with proper unification, no termination
guarantee, and a depth bound to keep the search finite (the interpreter
tells you when it was hit, i.e. when the answer set may be incomplete).

Differences from real Prolog, on purpose:

* unification includes the occurs check (Prolog omits it for speed, and
  `X = s(X)` quietly builds an infinite term);
* no cut, no arithmetic, no I/O — just SLD resolution over Horn clauses;
* `not` is negation as failure via a depth-bounded sub-proof.

Same syntax and parser as datalog.py, which *parses* compound terms but
rejects them at validation — run datalog.py on programs/09-peano.pl to see
the boundary stated as an error message.

CLI
---
    python3 prolog.py programs/09-peano.pl -q 'add(s(zero), s(s(zero)), X)'
    python3 prolog.py programs/09-peano.pl -q 'nat(X)' --max-solutions 5
"""

from __future__ import annotations

import argparse
import sys

from collections import defaultdict

from datalog import (Atom, Const, DatalogError, Literal, ParseError, Rule,
                     Struct, Var, parse, parse_goal)


# ---------------------------------------------------------------------------
# Unification (with occurs check)
# ---------------------------------------------------------------------------

def _walk(term, subst):
    while isinstance(term, Var) and term.name in subst:
        term = subst[term.name]
    return term


def _occurs(name, term, subst):
    term = _walk(term, subst)
    if isinstance(term, Var):
        return term.name == name
    if isinstance(term, Struct):
        return any(_occurs(name, a, subst) for a in term.args)
    return False


def unify(a, b, subst):
    """Return an extended substitution unifying a and b, or None."""
    a, b = _walk(a, subst), _walk(b, subst)
    if isinstance(a, Var):
        if isinstance(b, Var) and b.name == a.name:
            return subst
        if _occurs(a.name, b, subst):
            return None
        s = dict(subst)
        s[a.name] = b
        return s
    if isinstance(b, Var):
        return unify(b, a, subst)
    if isinstance(a, Const) and isinstance(b, Const):
        return subst if a.value == b.value else None
    if isinstance(a, Struct) and isinstance(b, Struct):
        if a.functor != b.functor or len(a.args) != len(b.args):
            return None
        for x, y in zip(a.args, b.args):
            subst = unify(x, y, subst)
            if subst is None:
                return None
        return subst
    return None


def _unify_atoms(goal, head, subst):
    if goal.pred != head.pred or len(goal.args) != len(head.args):
        return None
    for x, y in zip(goal.args, head.args):
        subst = unify(x, y, subst)
        if subst is None:
            return None
    return subst


def resolve(term, subst):
    """Deep-substitute for printing an answer term."""
    term = _walk(term, subst)
    if isinstance(term, Struct):
        return Struct(term.functor, tuple(resolve(a, subst) for a in term.args))
    return term


def _is_ground(atom, subst):
    """True iff every argument resolves to a variable-free term."""
    def ground(t):
        t = _walk(t, subst)
        if isinstance(t, Var):
            return False
        if isinstance(t, Struct):
            return all(ground(a) for a in t.args)
        return True
    return all(ground(a) for a in atom.args)


# ---------------------------------------------------------------------------
# SLD resolution
# ---------------------------------------------------------------------------

class PrologEngine:
    """Depth-bounded SLD resolution over Horn clauses.  After a solve, the
    `depth_hit` flag records whether the bound truncated the search (in
    which case "no more solutions" is not a proof of absence)."""

    def __init__(self, clauses):
        self.clauses = list(clauses)
        # index clauses by (pred, arity) so each resolution step only
        # scans candidates that could possibly unify; source order is
        # preserved within a bucket, so SLD semantics are unchanged
        self.by_pred = defaultdict(list)
        for c in self.clauses:
            self.by_pred[(c.head.pred, len(c.head.args))].append(c)
        self.counter = 0
        self.depth_hit = False

    def _rename(self, rule):
        """Standardise a clause apart with fresh variable names."""
        self.counter += 1
        n = self.counter

        def rt(term):
            if isinstance(term, Var):
                return Var("_R%d_%s" % (n, term.name))
            if isinstance(term, Struct):
                return Struct(term.functor, tuple(rt(a) for a in term.args))
            return term

        def ra(atom):
            return Atom(atom.pred, tuple(rt(a) for a in atom.args))

        return Rule(ra(rule.head),
                    tuple(Literal(ra(l.atom), l.negated) for l in rule.body))

    def solve(self, goals, subst=None, depth=100):
        """Yield substitutions proving the goal list, left to right."""
        if subst is None:
            subst = {}
        if not goals:
            yield subst
            return
        if depth <= 0:
            self.depth_hit = True
            return
        goal, rest = goals[0], goals[1:]
        if goal.negated:
            # Negation as failure, with two honesty guards.
            # (1) The goal must be ground: `not p(X)` with X unbound would
            # mean "no instance of p is provable at all", whose answer
            # depends on literal order — the classic "floundering" trap.
            if not _is_ground(goal.atom, subst):
                raise DatalogError(
                    "negation as failure needs a ground goal, but %s has "
                    "unbound variables — reorder the body so positive "
                    "literals bind them first" % (goal.atom,))
            # (2) Failure must be finite: if the sub-proof was cut off by
            # the depth bound, "no proof found" means unproven, not
            # disproven — so the negated goal must fail, not succeed.
            outer_hit = self.depth_hit
            self.depth_hit = False
            proved = False
            for _ in self.solve([Literal(goal.atom)], subst, depth - 1):
                proved = True
                break
            truncated = self.depth_hit
            self.depth_hit = outer_hit or truncated
            if proved or truncated:
                return
            yield from self.solve(rest, subst, depth - 1)
            return
        for clause in self.by_pred.get((goal.atom.pred,
                                        len(goal.atom.args)), ()):
            renamed = self._rename(clause)
            s2 = _unify_atoms(goal.atom, renamed.head, subst)
            if s2 is not None:
                yield from self.solve(list(renamed.body) + rest, s2,
                                      depth - 1)

    def query(self, atom, depth=100, max_solutions=None):
        """Solve a single goal; return (answers, incomplete) where answers
        is a list of {var_name: term} dicts for the query's variables and
        incomplete is True when the search was truncated — by the depth
        bound or the solution cap — so "no more answers" is not a proof
        of absence."""
        self.depth_hit = False
        qvars = []

        def collect(term):
            if isinstance(term, Var) and term not in qvars:
                qvars.append(term)
            elif isinstance(term, Struct):
                for a in term.args:
                    collect(a)

        for a in atom.args:
            collect(a)
        if max_solutions is not None and max_solutions <= 0:
            return [], False
        answers, seen = [], set()
        capped = False
        try:
            for s in self.solve([Literal(atom)], depth=depth):
                answer = {v.name: resolve(v, s) for v in qvars}
                key = tuple(str(answer[v.name]) for v in qvars)
                if key in seen:
                    continue
                seen.add(key)
                answers.append(answer)
                if max_solutions is not None and len(answers) >= max_solutions:
                    capped = True
                    break
        except RecursionError:
            raise DatalogError(
                "the proof search exceeded Python's recursion capacity; "
                "lower --depth (currently %d)" % depth)
        return answers, self.depth_hit or capped


def load(text):
    return PrologEngine(parse(text))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="prolog.py",
        description="Top-down SLD resolution over Horn clauses with "
                    "function symbols — what Datalog deliberately isn't.")
    ap.add_argument("file", help="Horn-clause program (.pl)")
    ap.add_argument("-q", "--query", action="append", default=[],
                    metavar="GOAL", help="goal to prove (repeatable)")
    ap.add_argument("--depth", type=int, default=100,
                    help="resolution depth bound (default 100)")
    ap.add_argument("--max-solutions", type=int, default=10,
                    help="stop after this many answers (default 10)")
    args = ap.parse_args(argv)

    with open(args.file) as fh:
        engine = load(fh.read())
    if not args.query:
        print("loaded %d clauses; pass -q 'goal(...)' to prove something"
              % len(engine.clauses))
        return 0
    for q in args.query:
        try:
            atom = parse_goal(q)
        except ParseError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
        print("?- %s" % atom)
        try:
            answers, incomplete = engine.query(
                atom, depth=args.depth, max_solutions=args.max_solutions)
        except DatalogError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
        if not answers:
            print("   false." if not incomplete else
                  "   false (search truncated at depth %d — unproven, "
                  "not disproven)." % args.depth)
            continue
        for answer in answers:
            if answer:
                print("   " + ",  ".join("%s = %s" % (v, t)
                                         for v, t in answer.items()))
            else:
                print("   true.")
        note = " (more may exist: search truncated)" if incomplete else ""
        print("   (%d solution%s%s)" % (len(answers),
                                        "" if len(answers) == 1 else "s",
                                        note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
