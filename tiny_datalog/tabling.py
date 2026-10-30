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

Negation is supported when the program is stratified, which is the
simplification pyDatalog also makes.  A negated subgoal `not q(a)`
belongs to a lower stratum, so q's tables can be *completed* first —
grown to fixpoint on their own, since nothing in them depends on the
rule asking — and then looked up.  Negation through recursion needs
full SLG resolution (Chen & Warren 1996), which suspends calls instead
of re-running them, detects when a group of tables is complete, and
*delays* negative literals it cannot yet decide; it computes the
well-founded semantics.  That is slg.py, the sequel to this module.

Aggregation is stratified the same way.  split_aggregates gives an
aggregate rule's body a table of its own, one answer per distinct
body solution; the aggregate completes that table first, a stratum
down, then folds it.  slg.py shares the split and the fold.

CLI
---
    python3 tabling.py programs/reachability.dl -q 'path(n5, X)'
    python3 tabling.py programs/left-recursive.dl -q 'ancestor(abe, X)'

Integrity constraints are checked after the queries, as datalog.py
checks them, and a violation exits 3.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from tiny_datalog.core import (
    check_query_atom, cli, Atom, Const, DatalogError, Literal, Rule,
    StratificationError, Var, format_fact, match, parse, parse_goal,
    read_program, sort_key, stratify, validate, aggregate_of, body_order,
    holds, is_comparison)
from tiny_datalog.datalog import _fold, _print_violations


# -- shared with slg.py: what a subgoal is, and how a clause meets one ------

def _bound_names(body):
    """The variables a body's positive literals bind, in order of first
    occurrence: every variable a solution of the body gives a value."""
    names = []
    for lit in body:
        if not lit.negated and not is_comparison(lit):
            names += [a.name for a in lit.atom.args
                      if isinstance(a, Var) and a.name not in names]
    return names


def constraint_goals(clauses):
    """Give each integrity constraint `:- body.` a rule a tabled engine
    can answer, `#constraint1(X, Y, ...) :- body.`, with every variable
    the body binds in its head: each answer is a counterexample, and
    checking the constraint is one query.  Nothing calls the new
    predicate, so no answer to any other query changes.  Returns
    (clauses, [(constraint, goal atom), ...])."""
    validate(clauses, constraints=True)   # refuse with the program's text
    out, goals = [], []
    for c in clauses:
        if not c.constraint:
            out.append(c)
            continue
        goal = Atom("#constraint%d" % (len(goals) + 1),
                    tuple(Var(n) for n in _bound_names(c.body)))
        out.append(Rule(goal, c.body))
        goals.append((c, goal))
    return out, goals


def counterexamples(goals, solve):
    """[(constraint, every body solution)] for each constraint violated,
    as Engine._counterexamples gives them, read off the answers that
    solve(goal atom) returns."""
    out = []
    for c, goal in goals:
        names = [a.name for a in goal.args]
        found = [dict(zip(names, t)) for t in sorted(solve(goal),
                                                     key=sort_key)]
        if found:
            out.append((c, found))
    return out


def split_aggregates(clauses):
    """Rewrite each aggregate rule so a tabled engine can evaluate it:
    `h(G, sum(V)) :- body.` becomes an auxiliary rule with one answer
    per distinct body solution, `h#1(G, V, ...) :- body.` (every body
    variable in its head), and the aggregate rule now reads that table,
    `h(G, sum(V)) :- h#1(G, V, ...).`  A name with `#` cannot clash
    with a predicate of the program.  Returns (clauses, {auxiliary
    predicate: the original rule}), the original for error messages."""
    out, sources = [], {}
    for c in clauses:
        if not (c.body and aggregate_of(c.head)):
            out.append(c)
            continue
        idx = aggregate_of(c.head)[0]
        aux = Atom("%s#%d" % (c.head.pred, len(sources) + 1),
                   tuple(a for j, a in enumerate(c.head.args) if j != idx)
                   + tuple(Var(n) for n in _bound_names(c.body)))
        sources[aux.pred] = c
        out += [Rule(aux, c.body), Rule(c.head, (Literal(aux),))]
    return out, sources


def index_clauses(clauses):
    """Validate a program for a tabled engine and index it: returns
    (arity, by_pred, sources), by_pred mapping (pred, arity) to (head,
    body) pairs, with aggregate rules split as split_aggregates does."""
    arity = validate(clauses)
    for c in clauses:
        if c.retract:
            raise DatalogError("retraction is incremental.py's job: %s" % c)
    clauses, sources = split_aggregates(clauses)
    by_pred = defaultdict(list)
    for c in clauses:
        # positive literals first: they bind; comparisons and negations
        # then test ground atoms (safety guarantees they are ground by
        # then)
        body = tuple(c.body[i] for i in body_order(c.body))
        head = c.head
        if c.body and aggregate_of(head):
            # head_seed matches values against variables, not `sum(V)`:
            # the aggregate's own position constrains nothing until the
            # fold, which filters on it (sources keeps the real head)
            idx = aggregate_of(head)[0]
            head = Atom(head.pred, head.args[:idx] + (Var("_#fold"),)
                        + head.args[idx + 1:])
        by_pred[(head.pred, len(head.args))].append((head, body))
    return arity, by_pred, sources


def fold_answers(rule, aux, tuples, pattern):
    """The answers an aggregate rule gives a call with this pattern,
    from its finished auxiliary table (the tuples of call `aux`): one
    fold per group, as datalog.py computes it."""
    idx, func, var = aggregate_of(rule.head)
    k, at = len(rule.head.args) - 1, aux.args.index(var)
    groups = defaultdict(list)
    for t in tuples:
        groups[t[:k]].append(t[at])
    for key, values in groups.items():
        out = key[:idx] + (_fold(func, values, rule),) + key[idx:]
        if all(p is None or p == v for p, v in zip(pattern, out)):
            yield out


def subsuming(finished, key):
    """A complete table whose call pattern is more general than key's
    (free wherever key is free, and agreeing where both are bound),
    or None; `finished` maps a predicate to its complete patterns.
    Its answers, filtered, are key's answers: subsumptive tabling,
    where each new call pattern otherwise gets its own table (variant
    tabling).  slg.py uses it; here tables complete too late to help."""
    pred, pattern = key
    for other in finished.get(pred, ()):
        if all(g is None or g == v for g, v in zip(other, pattern)):
            return (pred, other)
    return None


def call_pattern(atom, subst):
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


def head_seed(head, pattern):
    """Unify a clause head with a call pattern: one-way matching, as
    in a join, over the bound positions only (a free position, None,
    constrains nothing).  The substitution, or None if they clash."""
    bound = [(a, v) for a, v in zip(head.args, pattern) if v is not None]
    return match([a for a, _v in bound], [v for _a, v in bound], {})


class TabledEngine:
    """Iterative QSQR: tables keyed by call pattern, filled to fixpoint;
    a negated subgoal's tables are completed first, one stratum down.

    After query(), `tables` maps (pred, pattern) — pattern has a constant
    per bound argument and None per free one — to the set of full answer
    tuples for that subgoal, and `rounds` records the outer iterations."""

    def __init__(self, clauses):
        clauses, self.goals = constraint_goals(clauses)
        self.arity, self.by_pred, self.sources = index_clauses(clauses)
        try:
            stratify(clauses)           # refuses with the program's names
            # ...and the strata of the split program, where an
            # aggregate's auxiliary table sits below the aggregate
            self.strata = stratify(split_aggregates(clauses)[0])
        except StratificationError as exc:
            raise StratificationError(
                "%s.  Tabling under unstratified negation is full SLG "
                "resolution, which computes the well-founded semantics "
                "(Lesson 15); slg.py runs it top-down, datalog.py "
                "--models bottom-up."
                % str(exc).rstrip("."), exc.cycle) from exc
        self._reset()

    def _reset(self):
        self.tables = {}
        self.complete = set()   # tables known to hold every answer
        self.open = {}          # ...and the rest, in creation order (a
                                # dict: a set's order would vary per run)
        self.rounds = 0

    def _table(self, pred, pattern):
        key = (pred, pattern)
        if key not in self.tables:
            self.tables[key] = set()   # discovered a new subgoal, which
            self.open[key] = None      # the fixpoint will now revisit
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
        if is_comparison(lit):          # a test, never a subgoal
            if holds(lit.atom, subst):
                yield from self._prove(rest, subst)
            return
        key = (lit.atom.pred, call_pattern(lit.atom, subst))
        table = self._table(*key)
        if lit.atom.pred in self.sources:
            # an aggregate reads its auxiliary table only once complete:
            # it sits a stratum below, so completing it cannot need us
            if key not in self.complete:
                self._fixpoint(below=self.strata[lit.atom.pred])
            yield subst, table
            return
        if lit.negated:
            # `not q(a)` may only read a finished table.  q sits in a
            # lower stratum, so finishing it cannot need this rule.
            if key not in self.complete:
                self._fixpoint(below=self.strata.get(lit.atom.pred, 0))
            if key[1] not in table:     # the pattern is the ground atom
                yield from self._prove(rest, subst)
            return
        for ans in list(table):         # a negation below may add to it
            s = match(lit.atom.args, ans, subst)
            if s is not None:
                yield from self._prove(rest, s)

    def _answers_for(self, key):
        """Re-derive a subgoal's answers from its clauses, one step of
        head unification plus a tabled body proof."""
        pred, pattern = key
        for head, body in self.by_pred.get((pred, len(pattern)), ()):
            seed = head_seed(head, pattern)
            if seed is None:
                continue
            if body and body[0].atom.pred in self.sources:
                for _s, table in self._prove(body, seed):
                    yield from fold_answers(self.sources[body[0].atom.pred],
                                            body[0].atom, table, pattern)
                continue
            for s in self._prove(body, seed):
                yield tuple(a.value if isinstance(a, Const) else s[a.name]
                            for a in head.args)

    # -- the fixpoint --------------------------------------------------------

    def query(self, atom):
        """All answers to `atom`, computed by tabled top-down evaluation.
        Also populates self.tables / self.rounds for inspection.

        The tables are a *table space*, kept from query to query: every
        table is complete once a query returns, and the program cannot
        change, so a later query reads them instead of re-solving them.
        `rounds` counts the last query's rounds alone."""
        check_query_atom(atom, self.arity)
        root = (atom.pred, call_pattern(atom, {}))
        self.rounds = 0
        if root not in self.complete:
            self._table(*root)
            try:
                self._fixpoint()
            except DatalogError:
                self._reset()       # half-filled tables are not complete
                raise
        return {t for t in self.tables[root]
                if match(atom.args, t, {}) is not None}

    def counterexamples(self):
        """The violated integrity constraints, with every body solution,
        in the form Engine._counterexamples gives."""
        return counterexamples(self.goals, self.query)

    def _fixpoint(self, below=None):
        """Re-solve tables until none grows and no new subgoal appears.
        With `below`, only the tables of strata up to that one — the
        nested fixpoint a negation runs to complete what it reads; they
        are then marked complete.  Without, every table: the query's
        own fixpoint, whose rounds are the ones counted."""
        changed = True
        while changed:
            known = len(self.tables)
            changed = False
            if below is None:
                self.rounds += 1
            for key in list(self.open):       # complete tables cannot grow
                if below is not None and self.strata.get(key[0], 0) > below:
                    continue
                table = self.tables[key]
                for ans in list(self._answers_for(key)):
                    if ans not in table:
                        table.add(ans)
                        changed = True
            changed = changed or len(self.tables) != known
        done = {k for k in self.open
                if below is None or self.strata.get(k[0], 0) <= below}
        self.complete |= done
        for k in done:
            del self.open[k]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Tabled top-down (QSQR) evaluation of stratified "
                    "Datalog — handles left recursion SLD cannot.")
    ap.add_argument("file", help="Datalog program (.dl), stratified")
    ap.add_argument("-q", "--query", action="append", default=[],
                    metavar="ATOM", help="goal to solve (repeatable)")
    ap.add_argument("-t", "--tables", action="store_true",
                    help="also print every table (compare these with the "
                         "magic predicates from datalog.py --magic!)")
    args = ap.parse_args(argv)

    engine = TabledEngine(parse(read_program(args.file)))
    for q in args.query:
        atom = parse_goal(q)
        answers = engine.query(atom)
        print("?- %s   [tabled]" % atom)
        for tup in sorted(answers, key=sort_key):
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
    # each constraint is one more query, read from the same tables
    failed = engine.counterexamples()
    return 3 if _print_violations([c for c, _g in engine.goals],
                                  failed) else 0


if __name__ == "__main__":
    sys.exit(main())
