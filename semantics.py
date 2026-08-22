#!/usr/bin/env python3
"""
semantics.py — ground semantics: stable models and the well-founded
model.  (Lesson 5; implementation tour in Lesson 11.)

Stratifiability is a *syntactic* test, and rejection by the stratified
engine is not a semantic verdict: win(X) :- move(X, Y), not win(Y) is
unstratifiable yet has perfectly sensible stable models.  This module
computes the two classical semantics that answer the real question —
"what, if anything, does this program mean?":

* **Stable models** (Gelfond–Lifschitz, 1988).  A set of facts M is
  stable if it *justifies itself*: assume M is exactly what's true,
  simplify every `not` under that assumption (the "reduct"), and check
  that the simplified — now negation-free — program derives exactly M
  back.  No unsupported beliefs, no dropped conclusions.  A program with
  no stable model (the café paradox, `p :- not p`) is genuinely
  paradoxical.
* **The well-founded model** (Van Gelder–Ross–Schlipf, 1991).  Three
  valued and always defined: every fact comes out true, false, or
  *undefined*.  What can be settled is settled; what is genuinely
  circular is named as such.

Both are computed over the program's grounding, and the stable-model
search is exhaustive over candidate sets — fine for teaching-sized
programs, and honest about it.  Industrial ASP solvers (clingo) get the
same answers by conflict-driven search instead.
"""

from __future__ import annotations

from collections import defaultdict

from datalog import Const, DatalogError, _match, _sort_key, validate


def _instantiate_atom(atom, subst):
    return (atom.pred, tuple(a.value if isinstance(a, Const) else subst[a.name]
                             for a in atom.args))


def ground_program(clauses):
    """Ground the program.

    Returns (facts, ground_rules, candidates): facts is the set of ground
    atoms (pred, args) from unit clauses; ground_rules is a list of
    (head, pos_atoms, neg_atoms) triples over ground atoms; candidates is
    the set of rule-derivable ground atoms when every negation is assumed
    to succeed.

    `candidates` is an upper bound on any stable model: the
    Gelfond–Lifschitz operator is antimonotone (more assumed facts block
    more rules), so every stable model M satisfies M = Γ(M) ⊆ Γ(∅) — and
    Γ(∅) is exactly "derive with all negations granted".  The exhaustive
    search below therefore only needs subsets of this envelope.
    """
    validate(clauses)
    facts = {(r.head.pred, tuple(a.value for a in r.head.args))
             for r in clauses if not r.body}
    rules = [r for r in clauses if r.body]

    # Least model ignoring negation = the envelope of possibly-true atoms.
    rels = defaultdict(set)
    for pred, args in facts:
        rels[pred].add(args)

    def substitutions(rule):
        # Join the positive body literals against the envelope; negated
        # literals are skipped (treated as satisfied) at this stage.
        substs = [{}]
        for lit in rule.body:
            if lit.negated:
                continue
            new = []
            for s in substs:
                for tup in rels.get(lit.atom.pred, ()):
                    m = _match(lit.atom.args, tup, s)
                    if m is not None:
                        new.append(m)
            substs = new
        return substs

    changed = True
    while changed:
        changed = False
        for rule in rules:
            for s in substitutions(rule):
                pred, args = _instantiate_atom(rule.head, s)
                if args not in rels[pred]:
                    rels[pred].add(args)
                    changed = True

    # Instantiate every rule over the envelope: each grounding whose
    # positive body lies inside the envelope becomes one ground rule.
    ground_rules = []
    seen = set()
    for rule in rules:
        for s in substitutions(rule):
            gr = (_instantiate_atom(rule.head, s),
                  tuple(_instantiate_atom(l.atom, s)
                        for l in rule.body if not l.negated),
                  tuple(_instantiate_atom(l.atom, s)
                        for l in rule.body if l.negated))
            if gr not in seen:
                seen.add(gr)
                ground_rules.append(gr)
    candidates = {gr[0] for gr in ground_rules} - facts
    return facts, ground_rules, candidates


def _gamma(S, facts, ground_rules):
    """The Gelfond–Lifschitz operator: least model of the reduct of the
    ground program with respect to S.

    The reduct deletes every rule with a negative literal `not a` where
    a ∈ S, and strips the surviving rules' negative literals.  What's
    left is negation-free, so it has a unique least model — computed here
    by plain forward chaining.  M is a stable model iff Γ(M) == M.
    """
    derived = set(facts)
    changed = True
    while changed:
        changed = False
        for head, pos, neg in ground_rules:
            if head in derived:
                continue
            if any(a in S for a in neg):
                continue  # rule deleted by the reduct
            if all(a in derived for a in pos):
                derived.add(head)
                changed = True
    return derived


def stable_models(clauses, limit_atoms=16, grounding=None):
    """All stable models of the program, as sets of ground atoms (pred,
    args), EDB facts included.  Exhaustive search over subsets of the
    candidate atoms; small programs only, and says so.  Pass a
    precomputed `grounding` (from ground_program) to avoid regrounding."""
    facts, ground_rules, candidates = grounding or ground_program(clauses)
    atoms = sorted(candidates, key=lambda a: (a[0], _sort_key(a[1])))
    if len(atoms) > limit_atoms:
        raise DatalogError(
            "stable-model search is limited to %d candidate atoms; this "
            "program grounds to %d" % (limit_atoms, len(atoms)))
    models = []
    for mask in range(1 << len(atoms)):
        M = {atoms[i] for i in range(len(atoms)) if mask >> i & 1} | facts
        if _gamma(M, facts, ground_rules) == M:
            models.append(M)
    return models


def well_founded(clauses, grounding=None):
    """The well-founded (three-valued) model, via Van Gelder's alternating
    fixpoint.  Returns (true_atoms, undefined_atoms); everything else is
    false.

    The trick: Γ is antimonotone, so Γ∘Γ is monotone and has a least
    fixpoint T (the surely-true atoms) reachable by plain iteration.
    Γ(T) is then the upper envelope of the possibly-true; the gap
    Γ(T) - T is precisely the undefined zone — for the café paradox,
    exactly Bob's three atoms."""
    facts, ground_rules, _candidates = grounding or ground_program(clauses)
    T = set(facts)
    while True:
        upper = _gamma(T, facts, ground_rules)
        T2 = _gamma(upper, facts, ground_rules)
        if T2 == T:
            return T, upper - T
        T = T2
