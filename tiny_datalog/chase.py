#!/usr/bin/env python3
"""
chase.py — existential rules and the chase.  (Lesson 22.)

Datalog's safety condition says every head variable must be bound by
the body, and that is what keeps the universe of values closed: no rule
can mention anything the database did not already contain.  An
**existential rule** (a tuple-generating dependency, in database
theory's name for it) drops exactly that condition:

    works_in(E, D) :- employee(E).          % every employee works in
                                            % *some* department

D is bound by nothing, so it is read as "there exists a D".  Nobody
knows which department, so the engine invents a placeholder for it —
a **labelled null**, printed `_:n1` (RDF writes the same idea as a blank
node, `_:b1`) — and carries on.  That procedure is **the chase**, and
this module is it:

1. saturate the ordinary rules, with the base engine from datalog.py;
2. fire every existential rule whose body matches, inventing a fresh
   null for each existential variable;
3. repeat until a round invents nothing.

Two variants, chosen with --variant:

* **restricted** (the default): a trigger fires only if its head is not
  already satisfied — if *some* department for alice is already known,
  the rule has nothing to add.  Ordinary rules run first in every
  round (the "Datalog-first" order), so the check sees everything they
  imply.
* **oblivious**: every trigger fires once, satisfied or not.  Simpler,
  and it invents nulls the restricted chase would not.

Neither is guaranteed to stop: inventing values is precisely what the
safety condition was there to prevent (lesson 11's boundary, crossed
from the database side).  Whether the chase terminates is undecidable
in general, so the module does two things about it.  Before running,
it checks **weak acyclicity** (Fagin, Kolaitis, Miller and Popa, 2005),
a static condition that *guarantees* termination: draw a graph over
argument positions, mark the edges along which a rule invents a null,
and look for a cycle through a marked edge — a graph problem in the
same spirit as stratification.  And while running, it stops after
--max-nulls inventions and says which cycle is the likely culprit.

Answers that mention a null are reported, but are not **certain
answers**: they are true in every model only up to *which* value the
null stands for.  `manages(_:n2, sales)` says sales has a manager, not
who.

Where this stops
----------------
Positive rules only: no `not`, no aggregates, one atom per head (write
a second ordinary rule over the invented value where a conjunctive head
would be used).  No equality-generating dependencies, so two nulls
known to be the same thing are never merged; lesson 22's sameAs
section is about why that is the hard part.

CLI
---
    python3 chase.py programs/org-chart.dl
    python3 chase.py -q 'manages(M, D)' programs/org-chart.dl
    python3 chase.py --variant oblivious programs/org-chart.dl
"""

from __future__ import annotations

import argparse
import sys

from collections import defaultdict, deque
from dataclasses import dataclass

from tiny_datalog.core import (
    _format_value, aggregate_of, Atom, cli, Const, DatalogError, Literal,
    match, parse, parse_query_atom, read_program, Rule, Var, validate)
from tiny_datalog.datalog import Engine, Program


@dataclass(frozen=True)
class Null:
    """A labelled null: a value the chase invented to witness an
    existential.  Two nulls are equal only if they are the same null."""
    n: int

    def __str__(self):
        return "_:n%d" % self.n


def _format(v):
    return str(v) if isinstance(v, Null) else _format_value(v)


def format_atom(pred, tup):
    if not tup:
        return pred
    return "%s(%s)" % (pred, ", ".join(_format(v) for v in tup))


def _key(tup):
    # constants as core.sort_key orders them, then nulls in invention order
    return tuple((2, v.n, "") if isinstance(v, Null)
                 else (0, v, "") if isinstance(v, (int, float))
                 else (1, 0, str(v)) for v in tup)


def has_null(tup):
    return any(isinstance(v, Null) for v in tup)


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------

def _body_vars(rule):
    return {a.name for lit in rule.body for a in lit.atom.args
            if isinstance(a, Var)}


def existentials(rule):
    """The head variables no body literal binds, in head order."""
    bound = _body_vars(rule)
    seen = []
    for a in rule.head.args:
        if isinstance(a, Var) and a.name not in bound and a.name not in seen:
            seen.append(a.name)
    return seen


def check(clauses):
    """Validate a program of existential rules; return {pred: arity}.

    The core's checks apply to a *skeleton* of each rule in which the
    existential variables are replaced by a placeholder constant: that
    is exactly "safe, except for the variables we mean to invent"."""
    for c in clauses:
        if c.retract:
            raise DatalogError("a retraction is an update, not a statement:"
                               " %s" % c)
        if any(lit.negated for lit in c.body):
            raise DatalogError(
                "negation is not supported by the chase: %s.  With "
                "invented values, `not` would have to range over values "
                "not invented yet" % c)
        if c.body and aggregate_of(c.head):
            raise DatalogError("aggregates are not supported by the chase:"
                               " %s" % c)
    skeleton = []
    for c in clauses:
        ex = set(existentials(c)) if c.body else set()
        head = Atom(c.head.pred, tuple(
            Const(None) if isinstance(a, Var) and a.name in ex else a
            for a in c.head.args))
        skeleton.append(Rule(head, c.body, c.weight))
    return validate(skeleton)


# ---------------------------------------------------------------------------
# Weak acyclicity: termination as a graph problem
# ---------------------------------------------------------------------------

def position_graph(rules):
    """Edges between argument positions (pred, i), as Fagin et al. draw
    them.  For each variable a rule copies from body to head: a *normal*
    edge from each body position it occupies to each head position it
    occupies, and a *special* edge from each of those body positions to
    every head position holding an existential — the value there is
    invented *because* the body matched."""
    normal, special = set(), set()
    for rule in rules:
        body_pos = defaultdict(list)
        for lit in rule.body:
            for i, a in enumerate(lit.atom.args):
                if isinstance(a, Var):
                    body_pos[a.name].append((lit.atom.pred, i))
        ex = set(existentials(rule))
        ex_pos = [(rule.head.pred, i) for i, a in enumerate(rule.head.args)
                  if isinstance(a, Var) and a.name in ex]
        for i, a in enumerate(rule.head.args):
            if isinstance(a, Var) and a.name in body_pos:
                for p in body_pos[a.name]:
                    normal.add((p, (rule.head.pred, i)))
                    special.update((p, q) for q in ex_pos)
    return normal, special


def _path(edges, start, goal):
    """A shortest path start -> goal in the graph, as a node list."""
    succ = defaultdict(set)
    for u, v in edges:
        succ[u].add(v)
    prev, todo = {start: None}, deque([start])
    while todo:
        u = todo.popleft()
        if u == goal:
            path = []
            while u is not None:
                path.append(u)
                u = prev[u]
            return path[::-1]
        for v in sorted(succ[u]):
            if v not in prev:
                prev[v] = u
                todo.append(v)
    return None


def dangerous_cycle(rules):
    """None if the rules are weakly acyclic; otherwise a cycle through a
    special edge, as a list of (node, edge_kind_into_next) pairs."""
    normal, special = position_graph(rules)
    edges = normal | special
    for p, q in sorted(special):
        back = _path(edges, q, p)
        if back is not None:
            nodes = [p] + back          # p =*=> q -> ... -> p
            kinds = ["special"] + [
                "normal" if (u, v) in normal else "special"
                for u, v in zip(back, back[1:])]
            return list(zip(nodes, kinds + [None]))
    return None


def format_cycle(cycle):
    out = []
    for (pred, i), kind in cycle:
        out.append("%s[%d]" % (pred, i + 1))
        if kind:
            out.append("=*=>" if kind == "special" else "->")
    return " ".join(out)


# ---------------------------------------------------------------------------
# The chase
# ---------------------------------------------------------------------------

class ChaseBudget(DatalogError):
    pass


def _solutions(body, rels):
    """Every substitution satisfying the body: nested-loop joins, in a
    fixed order so that null numbering is the same on every run."""
    substs = [{}]
    for lit in body:
        rel = sorted(rels.get(lit.atom.pred, ()), key=_key)
        substs = [s2 for s in substs for tup in rel
                  for s2 in (match(lit.atom.args, tup, s),) if s2 is not None]
    return substs


def _saturate(rules, rels):
    """The ordinary rules, to fixpoint, by the base engine.  Facts may
    hold nulls: to the engine they are values like any other."""
    if not rules:
        return rels
    facts = [Rule(Atom(pred, tuple(Const(v) for v in tup)), ())
             for pred, tups in rels.items() for tup in tups]
    engine = Engine(Program(facts + list(rules)))
    engine.run()
    return engine.rels


class Chase:
    def __init__(self, clauses, variant="restricted", max_nulls=1000):
        if variant not in ("restricted", "oblivious"):
            raise DatalogError("unknown chase variant %r" % variant)
        self.arity = check(clauses)
        self.variant = variant
        self.max_nulls = max_nulls
        self.facts = [c for c in clauses if not c.body]
        rules = [c for c in clauses if c.body]
        self.plain = [r for r in rules if not existentials(r)]
        self.tgds = [r for r in rules if existentials(r)]
        self.idb = {r.head.pred for r in rules}
        self.cycle = dangerous_cycle(rules)
        self.rels = defaultdict(set)
        self.nulls = 0
        self.rounds = 0

    def _satisfied(self, head, s):
        """Is there already a fact matching the head, for *some* values
        of its existential variables?  (match leaves them unbound in s,
        so it binds them to whatever the fact holds.)"""
        return any(match(head.args, tup, s) is not None
                   for tup in self.rels.get(head.pred, ()))

    def _fresh(self):
        if self.nulls >= self.max_nulls:
            if self.cycle:
                why = ("the rules are not weakly acyclic -- %s -- so the "
                       "chase may never stop" % format_cycle(self.cycle))
            else:
                why = "the rules are weakly acyclic, so a larger budget " \
                      "will reach the end"
            raise ChaseBudget(
                "no fixpoint after inventing %d labelled nulls: %s.  "
                "(--max-nulls raises the budget.)" % (self.max_nulls, why))
        self.nulls += 1
        return Null(self.nulls)

    def run(self):
        for f in self.facts:
            self.rels[f.head.pred].add(tuple(a.value for a in f.head.args))
        fired = set()
        while True:
            self.rels = _saturate(self.plain, self.rels)
            self.rounds += 1
            invented = False
            for idx, rule in enumerate(self.tgds):
                for s in _solutions(rule.body, self.rels):
                    trigger = (idx, tuple(sorted(s.items(), key=str)))
                    if trigger in fired:
                        continue
                    fired.add(trigger)
                    if self.variant == "restricted" \
                            and self._satisfied(rule.head, s):
                        continue
                    s = dict(s)
                    for name in existentials(rule):
                        s[name] = self._fresh()
                    self.rels[rule.head.pred].add(tuple(
                        a.value if isinstance(a, Const) else s[a.name]
                        for a in rule.head.args))
                    invented = True
            if not invented:
                return self.rels

    def answers(self, atom):
        return sorted((tup for tup in self.rels.get(atom.pred, ())
                       if match(atom.args, tup, {}) is not None), key=_key)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="The chase: Datalog with existential rules.  A head "
                    "variable the body does not bind is invented, as a "
                    "labelled null.")
    ap.add_argument("file", help="program (.dl)")
    ap.add_argument("-q", "--query", action="append", default=[],
                    metavar="ATOM", help="query (repeatable)")
    ap.add_argument("-a", "--all", action="store_true",
                    help="print input relations too")
    ap.add_argument("--variant", choices=("restricted", "oblivious"),
                    default="restricted")
    ap.add_argument("--max-nulls", type=int, default=1000, metavar="N",
                    help="give up after inventing N nulls (default 1000)")
    args = ap.parse_args(argv)

    chase = Chase(parse(read_program(args.file)), args.variant,
                  args.max_nulls)
    if chase.cycle:
        print("not weakly acyclic: %s" % format_cycle(chase.cycle))
        print("  (a null can feed the rule that invents the next one; "
              "termination is not guaranteed)")
    else:
        print("weakly acyclic: the chase terminates on every database")
    chase.run()
    print("%s chase: %d round%s, %d labelled null%s invented"
          % (chase.variant, chase.rounds, "" if chase.rounds == 1 else "s",
             chase.nulls, "" if chase.nulls == 1 else "s"))
    print()

    if args.query:
        for q in args.query:
            atom = parse_query_atom(q, chase.arity)
            found = chase.answers(atom)
            print("?- %s" % atom)
            for tup in found:
                print("   %s.%s" % (format_atom(atom.pred, tup),
                                    "   [not certain: mentions a null]"
                                    if has_null(tup) else ""))
            certain = sum(1 for t in found if not has_null(t))
            print("   (%d answer%s, %d certain)"
                  % (len(found), "" if len(found) == 1 else "s", certain))
        return 0

    preds = sorted(set(chase.arity) if args.all else chase.idb)
    for pred in preds:
        tuples = sorted(chase.rels.get(pred, ()), key=_key)
        kind = "derived" if pred in chase.idb else "input"
        print("%% %s/%d (%s) — %d fact%s" % (
            pred, chase.arity[pred], kind, len(tuples),
            "" if len(tuples) == 1 else "s"))
        for tup in tuples:
            print(format_atom(pred, tup) + ".")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
