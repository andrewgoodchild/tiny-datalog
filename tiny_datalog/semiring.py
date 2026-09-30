#!/usr/bin/env python3
"""
semiring.py — Datalog over semirings: provenance and recursive aggregation.

A semiring (S, +, x, 0, 1) generalises what a derivation *carries*.  Every
fact holds a value from S; a rule instance multiplies the values of its
body facts; alternative derivations of the same fact add.  Choosing the
semiring changes the question the same program answers:

    bool     (or,  and)   plain Datalog — is the fact derivable?
    minplus  (min, +)     cheapest derivation — shortest paths
    count    (+,   x)     how many distinct derivations?
    why      (set union)  which base facts support it? (minimal witnesses)
    viterbi  (max, x)     probability of the most likely derivation

Facts take weights with `edge(a, b) @ 3.`; unweighted facts get the
semiring's `one`.  Run semirings on ordinary programs, not on magic-sets
rewritings: the magic guard predicates would multiply into every product
and corrupt the values.

Evaluation is Kleene fixpoint iteration of the immediate-consequence
operator — correct for the omega-continuous semirings provided here, with
a round cap that catches genuinely divergent combinations (counting
derivations in a cyclic graph really is infinite; so is the cheapest
route round a negative-cost cycle).  Positive programs
only: negation over semiring values needs more theory than this file
carries.

This is the entry point to the "Datalog over semirings" research thread:
Green–Karvounarakis–Tannen's provenance semirings (PODS 2007) and the
convergence theory of Abo Khamis–Ngo–Suciu and colleagues.

CLI
---
    python3 semiring.py --semiring minplus programs/routes.dl
    python3 semiring.py --semiring why -q 'path(a, e)' programs/routes.dl
"""

from __future__ import annotations

import argparse
import sys

from tiny_datalog.datalog import (
    Const, DatalogError, Program, format_atom, parse, read_program,
    validate, _aggregate_of, _match, _sort_key)


# ---------------------------------------------------------------------------
# Semirings
# ---------------------------------------------------------------------------

class Semiring:
    """Interface: zero, one, plus, times, fact_value, fmt — and
    `divergence`, the reason to give when values never settle."""
    name = "abstract"
    zero = None
    one = None
    divergence = "its values keep changing forever"

    def plus(self, a, b):
        raise NotImplementedError

    def times(self, a, b):
        raise NotImplementedError

    def fact_value(self, pred, tup, weight):
        """Value of a base fact; `weight` is its @ annotation or None."""
        return self.one if weight is None else weight

    def fmt(self, v):
        return str(v)


class BoolSemiring(Semiring):
    """(or, and): recovers ordinary Datalog."""
    name = "bool"
    zero, one = False, True

    def plus(self, a, b):
        return a or b

    def times(self, a, b):
        return a and b

    def fact_value(self, pred, tup, weight):
        return True

    def fmt(self, v):
        return "true" if v else "false"


class MinPlusSemiring(Semiring):
    """(min, +), the tropical semiring: cost of the cheapest derivation.
    Unweighted facts cost 0."""
    name = "minplus"
    zero, one = float("inf"), 0
    divergence = ("a negative-cost cycle makes costs fall without bound, "
                  "so there is no cheapest derivation")

    def plus(self, a, b):
        return min(a, b)

    def times(self, a, b):
        return a + b

    def fmt(self, v):
        return "%g" % v


class CountSemiring(Semiring):
    """(+, x) over the naturals: number of distinct derivations.  Weights
    are ignored — every base fact counts once, however often or with
    whatever weight it is written, and so does every rule: a program is a
    *set* of clauses, and saying one twice adds no new way to derive
    anything.  (Reading weights as multiplicities would give bag
    semantics; see lessons/08-semirings.md.)  Diverges when derivations
    are unbounded (cycles) — by design."""
    name = "count"
    zero, one = 0, 1
    divergence = ("a cycle among the derivations can be pumped forever, "
                  "so there are infinitely many of them to count")

    def plus(self, a, b):
        return a + b

    def times(self, a, b):
        return a * b

    def fact_value(self, pred, tup, weight):
        return 1


class ViterbiSemiring(Semiring):
    """(max, x) over [0, 1]: probability of the most likely single
    derivation.  See lessons/09-probabilistic.md for why this — and not
    "add up the probabilities" — is the honest semiring."""
    name = "viterbi"
    zero, one = 0.0, 1.0

    def plus(self, a, b):
        return max(a, b)

    def times(self, a, b):
        return a * b

    def fact_value(self, pred, tup, weight):
        if weight is None:
            return 1.0
        if not 0 <= weight <= 1:
            # outside [0, 1] a "probability" is meaningless, and max no
            # longer tames cycles (a loop of weight 2 grows forever)
            raise DatalogError(
                "viterbi weights are probabilities and must lie in "
                "[0, 1]: %s @ %s" % (format_atom(pred, tup), weight))
        return float(weight)

    def fmt(self, v):
        return "%.4g" % v


def _minimal(sets):
    """Keep only the minimal witness sets (absorption: A + A.B = A)."""
    return frozenset(s for s in sets
                     if not any(o < s for o in sets))


class WhySemiring(Semiring):
    """Why-provenance: each value is a set of minimal witness sets — the
    alternative sets of base facts sufficient to derive the fact."""
    name = "why"
    zero = frozenset()
    one = frozenset([frozenset()])

    def plus(self, a, b):
        return _minimal(a | b)

    def times(self, a, b):
        return _minimal(frozenset(x | y for x in a for y in b))

    def fact_value(self, pred, tup, weight):
        return frozenset([frozenset([format_atom(pred, tup)])])

    def fmt(self, v):
        parts = sorted("{%s}" % ", ".join(sorted(w)) for w in v)
        return " | ".join(parts) if parts else "{}"


SEMIRINGS = {sr.name: sr for sr in (
    BoolSemiring(), MinPlusSemiring(), CountSemiring(),
    ViterbiSemiring(), WhySemiring())}


# ---------------------------------------------------------------------------
# Evaluation: Kleene iteration of the immediate-consequence operator
# ---------------------------------------------------------------------------

def _eval_rule(rule, rels, sr):
    """Yield (head_tuple, value): every instantiation of the rule, with
    the product of its body facts' values."""
    pairs = [({}, sr.one)]
    for lit in rule.body:
        rel = rels.get(lit.atom.pred, {})
        args = lit.atom.args
        new = []
        for s, v in pairs:
            for tup, val in rel.items():
                m = _match(args, tup, s)
                if m is not None:
                    new.append((m, sr.times(v, val)))
        pairs = new
        if not pairs:
            return
    for s, v in pairs:
        yield (tuple(a.value if isinstance(a, Const) else s[a.name]
                     for a in rule.head.args), v)


class SemiringEngine:
    """Evaluates a positive program over a semiring.  After run(), `rels`
    maps each predicate to {tuple: value} and `rounds` records how many
    Kleene rounds the fixpoint took."""

    def __init__(self, clauses, semiring):
        if isinstance(semiring, str):
            try:
                semiring = SEMIRINGS[semiring]
            except KeyError:
                # the CLI is guarded by argparse choices; this is the
                # library caller's path, and a bare KeyError names the
                # typo without saying what would have been right
                raise DatalogError(
                    "unknown semiring %r — choose one of %s"
                    % (semiring, ", ".join(sorted(SEMIRINGS))))
        self.sr = semiring
        self.arity = validate(clauses)
        for r in clauses:
            if r.retract:
                # `q~.` is an update, not a fact; let the base engine's
                # Program reject it with its own explanation
                Program([r])
            if _aggregate_of(r.head):
                raise DatalogError(
                    "semiring evaluation does not compose with head "
                    "aggregation (a semiring already IS the aggregation "
                    "— see lessons 8 and 13): %s" % r)
            for lit in r.body:
                if lit.negated:
                    raise DatalogError(
                        "semiring evaluation is defined for positive "
                        "programs only (negated literal `%s` in: %s)"
                        % (lit, r))
        # A program is a set of clauses: a rule written twice is one rule
        # (otherwise count would see two derivations where there is one).
        self.rules = list(dict.fromkeys(r for r in clauses if r.body))
        self.idb = {r.head.pred for r in self.rules}
        self.base = {}
        seen_facts = set()
        for r in clauses:
            if r.body:
                continue
            tup = tuple(a.value for a in r.head.args)
            v = semiring.fact_value(r.head.pred, tup, r.weight)
            # Likewise a fact written twice with the same value is one
            # fact.  Keying on the *value*, not the written weight, is
            # what makes count ignore weights consistently.
            if (r.head.pred, tup, v) in seen_facts:
                continue
            seen_facts.add((r.head.pred, tup, v))
            d = self.base.setdefault(r.head.pred, {})
            # distinct values for the same tuple (parallel edges) combine
            d[tup] = semiring.plus(d[tup], v) if tup in d else v
        self.rels = {}
        self.rounds = 0

    def run(self, max_rounds=200):
        if max_rounds < 1:
            raise DatalogError(
                "max_rounds must be at least 1, not %r" % (max_rounds,))
        sr = self.sr
        current = {p: dict(d) for p, d in self.base.items()}
        for n in range(1, max_rounds + 1):
            new = {p: dict(d) for p, d in self.base.items()}
            for rule in self.rules:
                d = new.setdefault(rule.head.pred, {})
                for tup, val in _eval_rule(rule, current, sr):
                    d[tup] = sr.plus(d[tup], val) if tup in d else val
            new = {p: {t: v for t, v in d.items() if v != sr.zero}
                   for p, d in new.items()}
            new = {p: d for p, d in new.items() if d}
            if new == current:
                self.rels = current
                self.rounds = n
                return self
            current = new
        # Can we tell divergence from a small budget?  Round n accounts
        # for every derivation of height <= n.  A derivation that repeats
        # no fact on any branch has height below the number of facts, so
        # once the rounds outnumber the facts, values that still change
        # can only come from pumping a cycle — and that never stops.
        nfacts = sum(len(d) for d in current.values())
        if max_rounds > nfacts:
            raise DatalogError(
                "no fixpoint over the %s semiring: values still change "
                "after %d rounds although only %d facts exist, so no "
                "round budget will do — %s"
                % (sr.name, max_rounds, nfacts, sr.divergence))
        raise DatalogError(
            "no fixpoint after %d rounds over the %s semiring — with %d "
            "facts derived so far that is too few rounds to tell a deep "
            "derivation from a divergent one; raise it with --max-rounds"
            % (max_rounds, sr.name, nfacts))

    def value(self, pred, tup):
        return self.rels.get(pred, {}).get(tup, self.sr.zero)


def run_semiring(text, semiring, max_rounds=200):
    """Parse and evaluate a program over the named (or given) semiring."""
    return SemiringEngine(parse(text), semiring).run(max_rounds)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _positive_int(text):
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError("must be at least 1, not %d" % n)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Evaluate a positive Datalog program over a semiring.")
    ap.add_argument("file", help="Datalog program (.dl); facts may carry "
                                 "`@ weight` annotations")
    ap.add_argument("-s", "--semiring", default="minplus",
                    choices=sorted(SEMIRINGS),
                    help="semiring to evaluate over (default: minplus)")
    ap.add_argument("-q", "--query", action="append", default=[],
                    metavar="ATOM", help="query atom (repeatable)")
    ap.add_argument("--max-rounds", type=_positive_int, default=200,
                    help="Kleene round budget before giving up (default 200)")
    args = ap.parse_args(argv)

    try:
        engine = run_semiring(read_program(args.file),
                              args.semiring, args.max_rounds)
    except DatalogError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    sr = engine.sr
    print("Semiring: %s   (fixpoint after %d rounds)" % (sr.name, engine.rounds))
    if args.query:
        from tiny_datalog.datalog import _parse_query_atom
        for q in args.query:
            try:
                atom = _parse_query_atom(q, engine.arity)
            except DatalogError as exc:
                print("error: %s" % exc, file=sys.stderr)
                return 1
            print("?- %s" % atom)
            hits = [(t, v) for t, v in engine.rels.get(atom.pred, {}).items()
                    if _match(atom.args, t, {}) is not None]
            for t, v in sorted(hits, key=lambda x: _sort_key(x[0])):
                print("   %s = %s" % (format_atom(atom.pred, t), sr.fmt(v)))
            print("   (%d answer%s)" % (len(hits), "" if len(hits) == 1 else "s"))
        return 0
    for pred in sorted(engine.idb):
        d = engine.rels.get(pred, {})
        print("%% %s/%d — %d fact%s" % (pred, engine.arity[pred], len(d),
                                        "" if len(d) == 1 else "s"))
        for tup in sorted(d, key=_sort_key):
            print("%s = %s" % (format_atom(pred, tup), sr.fmt(d[tup])))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
