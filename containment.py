#!/usr/bin/env python3
"""
containment.py — query containment and minimisation for conjunctive
queries, by homomorphism.  (Lesson 15.)

Two questions an optimiser asks that evaluation never does:

* **Containment.** Does Q1 return a subset of Q2's answers, on *every*
  database?  Not "on this data" — on all data.
* **Minimisation.** Does Q have redundant atoms — a smaller body giving
  identical answers everywhere?

Chandra and Merlin (1977) answered both with one idea: for conjunctive
queries, **Q2 ⊇ Q1 iff there is a homomorphism from Q2's body into Q1's
body** that fixes the head variables.  Containment, a statement about
infinitely many databases, becomes a finite search for a variable
mapping.

The engine already contains most of this.  `datalog._match` maps a rule
body into the *database* — a set of ground atoms.  A homomorphism here
maps a rule body into *another rule body*, whose variables act like
fresh constants ("freezing" the query into a canonical database).  Same
search, one level up the abstraction; that observation is the whole
lesson, and it is why this module is short.

The price is complexity: homomorphism-finding is NP-complete (it is
graph colouring in disguise), so containment is too.  Classic queries
are small, and the backtracking search below is the standard practical
answer.

CLI
---
    python3 containment.py programs/minimise.dl
    python3 containment.py --contains 'q(X) :- e(X, Y), e(Y, Z).' \\
                           'q(X) :- e(X, Y).'
"""

from __future__ import annotations

import argparse
import sys

from datalog import Const, DatalogError, Var, parse, validate


def _extend(mapping, source_args, target_args):
    """Extend a variable mapping so source_args maps onto target_args."""
    out = dict(mapping)
    for s, t in zip(source_args, target_args):
        if isinstance(s, Const):
            if s != t:
                return None
        elif s.name in out:
            if out[s.name] != t:
                return None
        else:
            out[s.name] = t
    return out


def find_homomorphism(source, target, seed=None):
    """A mapping of source's variables to target's terms such that every
    source atom lands on some target atom, or None.

    Backtracking search: try every target atom for the first source
    atom, recurse.  This is exactly `_match`'s job with a target of
    non-ground atoms instead of tuples."""
    mapping = dict(seed or {})

    def search(i, current):
        if i == len(source):
            return current
        atom = source[i]
        for candidate in target:
            if (candidate.pred != atom.pred
                    or len(candidate.args) != len(atom.args)):
                continue
            extended = _extend(current, atom.args, candidate.args)
            if extended is not None:
                found = search(i + 1, extended)
                if found is not None:
                    return found
        return None

    return search(0, mapping)


def _bodies(rule):
    for lit in rule.body:
        if lit.negated:
            raise DatalogError(
                "containment by homomorphism is a conjunctive-query "
                "result; negation needs different theory: %s" % rule)
    return [lit.atom for lit in rule.body]


def _head_seed(outer, inner):
    """Head variables correspond positionally and must be preserved."""
    if len(outer.head.args) != len(inner.head.args):
        return None
    seed = {}
    for a, b in zip(outer.head.args, inner.head.args):
        if isinstance(a, Var):
            if a.name in seed and seed[a.name] != b:
                return None
            seed[a.name] = b
        elif a != b:
            return None
    return seed


def contains(outer, inner):
    """True if `outer` ⊇ `inner`: on every database, every answer to
    inner is an answer to outer.  Decided by a homomorphism from outer's
    body into inner's (Chandra–Merlin)."""
    seed = _head_seed(outer, inner)
    if seed is None:
        return False
    return find_homomorphism(_bodies(outer), _bodies(inner), seed) is not None


def equivalent(a, b):
    return contains(a, b) and contains(b, a)


def minimise(rule):
    """The smallest equivalent body: repeatedly drop an atom whose loss
    a homomorphism can repair.  For conjunctive queries this greedy
    procedure is safe — the minimal form is unique up to renaming, so
    the order atoms are tried in cannot change the result."""
    atoms = _bodies(rule)
    head_vars = {a.name for a in rule.head.args if isinstance(a, Var)}
    changed = True
    while changed:
        changed = False
        for i in range(len(atoms)):
            reduced = atoms[:i] + atoms[i + 1:]
            if not reduced:
                continue
            seed = {v: Var(v) for v in head_vars}
            if find_homomorphism(atoms, reduced, seed) is not None:
                atoms = reduced
                changed = True
                break
    return atoms


def _fmt(head, atoms):
    return "%s :- %s." % (head, ", ".join(str(a) for a in atoms))


def _parse_query_rule(text):
    clauses = parse(text if text.rstrip().endswith(".") else text + ".")
    if len(clauses) != 1 or not clauses[0].body:
        raise DatalogError("expected a single rule: %r" % text)
    validate(clauses)
    return clauses[0]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="containment.py",
        description="Conjunctive-query containment and minimisation by "
                    "homomorphism (Chandra–Merlin).")
    ap.add_argument("file", nargs="?",
                    help="program whose rules should be minimised")
    ap.add_argument("--contains", nargs=2, metavar=("OUTER", "INNER"),
                    help="test whether OUTER contains INNER")
    args = ap.parse_args(argv)

    try:
        if args.contains:
            outer = _parse_query_rule(args.contains[0])
            inner = _parse_query_rule(args.contains[1])
            fwd, bwd = contains(outer, inner), contains(inner, outer)
            print("outer: %s" % outer)
            print("inner: %s" % inner)
            if fwd and bwd:
                print("=> equivalent (each contains the other)")
            elif fwd:
                print("=> outer contains inner, on every database")
            elif bwd:
                print("=> inner contains outer, on every database")
            else:
                print("=> neither contains the other")
            return 0

        if not args.file:
            ap.error("give a program to minimise, or use --contains")
        with open(args.file) as fh:
            clauses = parse(fh.read())
        validate(clauses)
        for rule in clauses:
            if not rule.body:
                continue
            if any(lit.negated for lit in rule.body):
                print("%s\n  (skipped: negation is outside the theory)"
                      % rule)
                continue
            atoms = minimise(rule)
            before = len(rule.body)
            if len(atoms) == before:
                print("%s\n  already minimal (%d atom%s)"
                      % (rule, before, "" if before == 1 else "s"))
            else:
                print("%s\n  minimises to %s   (%d atoms -> %d)"
                      % (rule, _fmt(rule.head, atoms), before, len(atoms)))
    except DatalogError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
