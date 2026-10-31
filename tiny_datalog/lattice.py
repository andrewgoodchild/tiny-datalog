"""
lattice.py — answer subsumption's front end, for both tabled engines:
which predicates recurse through min or max, and whether that is sound.

Stratification refuses an aggregate inside a recursive cycle (lesson
13), and for count and sum it must: a count that feeds its own
derivation has no stable answer.  Min and max are different.  They
are lattice joins, so a table can keep one best answer per group and
let a better one replace it, and the recursion still reaches a
fixpoint, the way the powerset lattice does for ordinary tables.
XSB calls this answer subsumption, and B-Prolog and SWI-Prolog
mode-directed tabling; Flix and Ascent build Datalog on lattices for
the same reason.

It gives the answer the stratified program would, where every
recursive read sees every value and the min is taken once at the end,
provided each rule is monotone: a better value read can only help.
lattices() checks that rule by rule, conservatively, and refuses the
rest.  free_value() and improve() keep the tables, for
tablespace.TableSpace;
lesson 15 tells the story.
"""

from __future__ import annotations

from tiny_datalog.core import (
    _tarjan, Atom, Const, DatalogError, Literal, Rule, aggregate_of,
    is_comparison)
from tiny_datalog.datalog import _fold


def lattices(clauses):
    """Answer subsumption: the predicates that recurse through min or
    max, as {pred: (index, func, a rule)}.  Such a predicate's table
    keeps one answer per group, the best so far, and a better one
    replaces it; the fold happens as answers arrive, not after.

    That is sound only if a better value read can never cost the head
    an answer, so each recursive read's value may appear only in the
    head's aggregate or on the side of a comparison that improving it
    keeps true (`T <= D` for min).  The recursion must be direct, every
    rule of the predicate must take the same aggregate, and `not` on
    it is refused (read the table through a plain rule instead)."""
    rules = [c for c in clauses if c.body]
    edges = [(c.head.pred, lit.atom.pred, False) for c in rules
             for lit in c.body if not is_comparison(lit)]
    scc = _tarjan({p for e in edges for p in e[:2]}, edges)
    found = {}
    for c in rules:
        agg = aggregate_of(c.head)
        if agg and agg[1] in ("min", "max") and any(
                scc[lit.atom.pred] == scc[c.head.pred] for lit in c.body
                if not is_comparison(lit)):
            found[c.head.pred] = agg[:2] + (c,)
    for c in rules:
        lattice = found.get(c.head.pred)
        for lit in c.body:
            if lit.negated and lit.atom.pred in found:
                raise DatalogError("not %s reads a table that keeps only "
                                   "its best answers: %s" % (lit.atom, c))
            if lattice and not is_comparison(lit) and lit.atom.pred != \
                    c.head.pred and scc[lit.atom.pred] == scc[c.head.pred]:
                raise DatalogError(
                    "recursion through %s must be direct, but %s and %s "
                    "depend on each other: %s"
                    % (lattice[1], c.head.pred, lit.atom.pred, c))
        if lattice:
            agg = aggregate_of(c.head)
            if not agg or agg[:2] != lattice[:2]:
                raise DatalogError("%s recurses through %s, so every rule "
                                   "for it must take %s at the same place: "
                                   "%s" % (c.head.pred, lattice[1],
                                           lattice[1], c))
            _check_monotone(c, *agg[:2])
    return found


def _check_monotone(rule, idx, func):
    """Refuse a recursive rule of a lattice predicate unless a better
    value read can only help it (lattices() says why)."""
    small = {"<": 0, "<=": 0, ">": 1, ">=": 1}  # the smaller side
    for i, lit in enumerate(rule.body):
        if lit.negated or lit.atom.pred != rule.head.pred:
            continue
        v = lit.atom.args[idx]
        uses = [u for j, u in enumerate(rule.body)
                if j != i and v in u.atom.args]
        if isinstance(v, Const) or v in rule.head.args or any(
                u.atom.pred not in small or
                (u.atom.args.index(v) == small[u.atom.pred])
                != (func == "min") for u in uses):
            raise DatalogError(
                "recursion through %s needs each rule to be monotone: a "
                "%s value from %s must never cost the head an answer, so "
                "it may appear only in the head's %s or on the %s side "
                "of a comparison: %s"
                % (func, "smaller" if func == "min" else "larger",
                   lit.atom, func, "smaller" if func == "min"
                   else "larger", rule))


def unfold_lattices(clauses, lattice, strict=False):
    """The program with each lattice rule's `min(V)` as plain V: its
    table keeps the best answer as it goes, so it needs no fold.  With
    strict, for stratify alone, a read of a lattice predicate from any
    other predicate is marked `not`: like a negation, it must wait for
    the table to complete, or answers the table later drops would
    stay in the reader's."""
    out = []
    for c in clauses:
        if c.head.pred in lattice and c.body:
            idx = lattice[c.head.pred][0]
            args = list(c.head.args)
            args[idx] = aggregate_of(c.head)[2]
            c = Rule(Atom(c.head.pred, tuple(args)), c.body)
        elif strict:
            c = Rule(c.head, tuple(
                Literal(lit.atom, True) if lit.atom.pred in lattice
                else lit for lit in c.body), c.weight, c.retract,
                c.constraint)
        out.append(c)
    return out


def free_value(lattice, pred, pattern):
    """A call pattern with a lattice predicate's value position free:
    the best value is known only once every value is in, so a call
    that binds it reads the whole group, and filters."""
    if pred not in lattice:
        return pattern
    i = lattice[pred][0]
    return pattern[:i] + (None,) + pattern[i + 1:]


def improve(lattice, best, key, answers, tup):
    """Whether a new answer may enter table `key`: always, unless the
    table is a lattice's; then only if it betters its group's best,
    which is returned second for the caller to drop (or None).  `best`
    maps a lattice table to {group: its answer}, built on first use."""
    if key[0] not in lattice:
        return True, None
    i, func, rule = lattice[key[0]]
    if key not in best:                   # first use, or restored
        best[key] = {t[:i] + t[i + 1:]: t for t in answers}
    group = tup[:i] + tup[i + 1:]
    old = best[key].get(group)
    if old is not None and _fold(func, [tup[i], old[i]], rule) == old[i]:
        return False, None
    best[key][group] = tup
    return True, old
