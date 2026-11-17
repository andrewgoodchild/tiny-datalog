#!/usr/bin/env python3
"""
semantics.py — ground semantics: stable models and the well-founded
model.  (Lesson 5, which ends with a tour of this module.)

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

Both are computed over the program's grounding.  Stable models are
found two ways, which must agree.  The exhaustive search tries every
candidate set, which is the definition and stops being possible at a
couple of dozen atoms.  The default hands the guessing to a SAT solver
(sat.py) and keeps the definition as the *check*: each candidate that
fails it teaches the solver a clause.  Industrial ASP solvers (clingo)
go further, learning clauses inside the solver from every dead end.
"""

from __future__ import annotations

from tiny_datalog.core import (
    DatalogError, Rule, aggregate_of, is_comparison, sort_key, validate)
from tiny_datalog.datalog import Engine, Program
from tiny_datalog.sat import solve


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
    for r in clauses:
        if r.retract:
            # `q~.` is an update, not a fact; let the base engine's
            # Program reject it with its own explanation
            Program([r])
        if r.body and aggregate_of(r.head):
            raise DatalogError(
                "stable-model and well-founded semantics for aggregates "
                "are beyond this module (and still debated in the "
                "literature): %s" % r)
    facts = {(r.head.pred, tuple(a.value for a in r.head.args))
             for r in clauses if not r.body}
    rules = [r for r in clauses if r.body]

    # Least model ignoring negation = the envelope of possibly-true atoms.
    # Strip every negated literal (treat it as satisfied) and let the
    # ordinary engine compute that least model: a positive program
    # always stratifies, and safety still holds, because a negated
    # literal never binds a variable the positives didn't.
    positive = [Rule(r.head, tuple(l for l in r.body if not l.negated))
                for r in rules]
    engine = Engine(Program([r for r in clauses if not r.body] + positive))
    engine.run()

    def ground(atom, s):
        return (atom.pred, engine.instantiate(atom, s))

    # Instantiate every rule over the envelope: each grounding whose
    # positive body lies inside the envelope becomes one ground rule,
    # negated literals and all.  A comparison is settled by grounding
    # (the substitutions only include those it allows), so it leaves
    # no ground atom behind.
    ground_rules = []
    seen = set()
    for rule, pos_rule in zip(rules, positive):
        for s in engine.substitutions(pos_rule):
            gr = (ground(rule.head, s),
                  tuple(ground(l.atom, s) for l in rule.body
                        if not l.negated and not is_comparison(l)),
                  tuple(ground(l.atom, s) for l in rule.body if l.negated))
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


def stable_models(clauses, limit_models=256, grounding=None,
                  exhaustive=False, limit_atoms=16, log=None):
    """All stable models of the program, as sets of ground atoms (pred,
    args), EDB facts included.  Pass a precomputed `grounding` (from
    ground_program) to avoid regrounding.

    Two searches give the same models.  `exhaustive=True` is the
    definition run as written: try every subset of the candidate
    atoms and keep those Γ maps to themselves.  It doubles with every
    atom, so it stops at `limit_atoms`.  The default asks a SAT solver
    for candidates worth trying (see _search), and is limited by how
    many models there are, not by how many atoms.  It appends what it
    did to `log`, if given: ("stable", atoms) for each model found and
    ("unfounded", atoms) for each candidate refused, facts left out."""
    facts, ground_rules, candidates = grounding or ground_program(clauses)
    atoms = sorted(candidates, key=lambda a: (a[0], sort_key(a[1])))
    if not exhaustive:
        return _search(facts, ground_rules, atoms, limit_models, log)
    if len(atoms) > limit_atoms:
        raise DatalogError(
            "exhaustive stable-model search is limited to %d candidate "
            "atoms; this program grounds to %d"
            % (limit_atoms, len(atoms)))
    models = []
    for mask in range(1 << len(atoms)):
        M = {atoms[i] for i in range(len(atoms)) if mask >> i & 1} | facts
        if _gamma(M, facts, ground_rules) == M:
            models.append(M)
    return models


def _completion(facts, ground_rules, number):
    """The ground program as clauses over one variable per candidate
    atom (`number`) and one more per rule body.  Returns (clauses,
    [(head, positive body, body variable)]).

    Two things are said.  *Every rule holds*: if its body is true, so
    is its head.  *Every true atom is supported*: some rule for it has
    a true body.  Together they are Clark's completion, and their
    models are the "supported" ones, which include every stable model.
    Atoms already settled are simplified away: a fact is true, and an
    atom outside the candidates is false."""
    cnf, bodies, support = [], [], {a: [] for a in number}
    for head, pos, neg in ground_rules:
        if head in facts or any(a in facts for a in neg):
            continue                        # already true, or never fires
        pos = [number[a] for a in pos if a not in facts]
        neg = [number[a] for a in neg if a in number]
        body = len(number) + len(bodies) + 1
        bodies.append((head, set(pos), body))
        cnf += [[-body, p] for p in pos] + [[-body, -n] for n in neg]
        cnf.append([body] + [-p for p in pos] + neg)    # body <-> its literals
        cnf.append([-body, number[head]])               # the rule holds
        support[head].append(body)
    cnf += [[-number[a]] + support[a] for a in number]  # true => supported
    return cnf, bodies


def _search(facts, ground_rules, atoms, limit_models, log=None):
    """Stable models by propose, check, constrain (lesson 5; the loop
    is lesson 26's, with atoms where that has rules).

    The solver proposes a supported model M.  The check is the
    definition: is Γ(M) = M?  If so M is stable, and since no stable
    model contains another, one clause forbids everything above it.
    If not, the atoms Γ failed to rebuild, U = M - Γ(M), hold each
    other up and nothing else does: an **unfounded set**.  The clause
    learned says that an atom of U may be true only if a rule for some
    atom of U has a true body that does not itself lean on U (a *loop
    formula*, Lin and Zhao 2004).  It rules out this M and every other
    candidate making the same circular argument."""
    number = {a: i + 1 for i, a in enumerate(atoms)}
    cnf, bodies = _completion(facts, ground_rules, number)
    models, log = [], [] if log is None else log
    while True:
        true = solve(cnf)
        if true is None:
            return models
        M = {atoms[i - 1] for i in true if i <= len(atoms)} | facts
        least = _gamma(M, facts, ground_rules)
        if least == M:
            if len(models) == limit_models:
                raise DatalogError(
                    "stable-model search is limited to %d models, and "
                    "this program (%d candidate atoms) has more"
                    % (limit_models, len(atoms)))
            models.append(M)
            log.append(("stable", M - facts))
            cnf.append([-number[a] for a in M - facts])
            continue
        log.append(("unfounded", M - least))
        unfounded = {number[a] for a in M - least}
        outside = [body for head, pos, body in bodies
                   if number[head] in unfounded and not pos & unfounded]
        cnf += [[-a] + outside for a in sorted(unfounded)]


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
