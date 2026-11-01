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

from collections import Counter

from tiny_datalog.core import (
    _tarjan, Atom, Const, DatalogError, Literal, Rule, aggregate_of,
    is_comparison)
from tiny_datalog.datalog import _fold


def lattices(clauses):
    """Answer subsumption: the predicates that recurse through min or
    max, as {pred: (index, func, a rule, component)}.  Such a
    predicate's table keeps one answer per group, the best so far, and
    a better one replaces it; the fold happens as answers arrive, not
    after.  `component` names its strongly connected component: the
    predicates that recurse through each other, which must all take the
    same aggregate.

    That is sound only if a better value read can never cost the head
    an answer, so each recursive read's value may appear only in the
    head's aggregate or on the side of a comparison that improving it
    keeps true (`T <= D` for min), or in a test that a partner rule
    negates (_paired).  Every rule of the predicate must take the same
    aggregate, and `not` on it is refused (read the table through a
    plain rule instead)."""
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
            found[c.head.pred] = agg[:2] + (c, scc[c.head.pred])
    for c in rules:
        lattice = found.get(c.head.pred)
        for lit in c.body:
            if lit.negated and lit.atom.pred in found:
                raise DatalogError("not %s reads a table that keeps only "
                                   "its best answers: %s" % (lit.atom, c))
            other = None if is_comparison(lit) else found.get(lit.atom.pred)
            if lattice and not is_comparison(lit) and \
                    scc[lit.atom.pred] == lattice[3] and \
                    (other is None or other[1] != lattice[1]):
                raise DatalogError(
                    "recursion through %s must stay among predicates that "
                    "take %s, but %s and %s depend on each other and %s %s: "
                    "%s" % (lattice[1], lattice[1], c.head.pred,
                            lit.atom.pred, lit.atom.pred,
                            "takes " + other[1] if other
                            else "does not take " + lattice[1], c))
        if lattice:
            agg = aggregate_of(c.head)
            if not agg or agg[:2] != lattice[:2]:
                raise DatalogError("%s recurses through %s, so every rule "
                                   "for it must take %s at the same place: "
                                   "%s" % (c.head.pred, lattice[1],
                                           lattice[1], c))
            _check_monotone(c, lattice[1], found, rules)
    return found


SMALL = {"<": 0, "<=": 0, ">": 1, ">=": 1}       # a comparison's smaller side
NEGATE = {"<": ">=", "<=": ">", ">": "<=", ">=": "<"}
FLIP = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}


def _check_monotone(rule, func, found, rules):
    """Refuse a recursive rule of a lattice predicate unless a better
    value read can only help it (lattices() says why)."""
    comp = found[rule.head.pred][3]
    for i, lit in enumerate(rule.body):
        read = found.get(lit.atom.pred)
        if lit.negated or read is None or read[3] != comp:
            continue
        v = lit.atom.args[read[0]]
        wrong = [u for j, u in enumerate(rule.body)
                 if j != i and v in u.atom.args and (
                     u.atom.pred not in SMALL or
                     (u.atom.args.index(v) == SMALL[u.atom.pred])
                     != (func == "min"))]
        if isinstance(v, Const) or v in rule.head.args or wrong and not (
                len(wrong) == 1 and _paired(rule, wrong[0], rules)):
            raise DatalogError(
                "recursion through %s needs each rule to be monotone: a "
                "%s value from %s must never cost the head an answer, so "
                "it may appear only in the head's %s, on the %s side "
                "of a comparison, or in a comparison that a rule otherwise "
                "the same negates: %s"
                % (func, "smaller" if func == "min" else "larger",
                   lit.atom, func, "smaller" if func == "min"
                   else "larger", rule))


def _paired(rule, test, rules):
    """Whether another rule is this one with `test` negated, and both
    take one of test's operands as their value.  Then the pair derives
    `if test then x else y`, with x and y drawn from the operands: one
    of them, or their min or max, and each of those is monotone in
    both.  It is how min(V, W) is written without arithmetic, as a
    bottleneck path needs (lesson 15)."""
    if test.atom.pred not in SMALL:
        return False
    a, b = test.atom.args
    op = NEGATE[test.atom.pred]
    negations = {Atom(op, (a, b)), Atom(FLIP[op], (b, a))}
    idx, _func, value = aggregate_of(rule.head)
    rest = Counter(rule.body)
    rest[test] -= 1
    group = rule.head.args[:idx] + rule.head.args[idx + 1:]
    for other in rules:
        agg = aggregate_of(other.head)
        if other.head.pred != rule.head.pred or not agg or \
                other.head.args[:idx] + other.head.args[idx + 1:] != group:
            continue
        for lit in other.body:
            if not lit.negated and lit.atom in negations:
                theirs = Counter(other.body)
                theirs[lit] -= 1
                if +theirs == +rest and {value, agg[2]} <= {a, b}:
                    return True
    return False


def outside(lattice, reader, pred):
    """Whether a rule for `reader` reads lattice `pred` from outside
    its cycle.  Such a read waits for the table to complete, as `not`
    does: an answer the table later dropped would stay in the reader's."""
    return pred in lattice and (reader not in lattice or
                                lattice[reader][3] != lattice[pred][3])


def unfold_lattices(clauses, lattice, strict=False):
    """The program with each lattice rule's `min(V)` as plain V: its
    table keeps the best answer as it goes, so it needs no fold.  With
    strict, for stratify alone, a read of a lattice predicate from
    outside its cycle (outside()) is marked `not`: like a negation, it
    must wait for the table to complete."""
    out = []
    for c in clauses:
        if strict and c.body:
            c = Rule(c.head, tuple(
                Literal(lit.atom, True)
                if outside(lattice, c.head.pred, lit.atom.pred) else lit
                for lit in c.body), c.weight, c.retract, c.constraint)
        if c.head.pred in lattice and c.body:
            idx = lattice[c.head.pred][0]
            args = list(c.head.args)
            args[idx] = aggregate_of(c.head)[2]
            c = Rule(Atom(c.head.pred, tuple(args)), c.body)
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
    i, func, rule = lattice[key[0]][:3]
    if key not in best:                   # first use, or restored
        best[key] = {t[:i] + t[i + 1:]: t for t in answers}
    group = tup[:i] + tup[i + 1:]
    old = best[key].get(group)
    if old is not None and _fold(func, [tup[i], old[i]], rule) == old[i]:
        return False, None
    best[key][group] = tup
    return True, old
