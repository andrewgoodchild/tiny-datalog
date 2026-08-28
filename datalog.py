#!/usr/bin/env python3
"""
datalog.py — a small Datalog engine with semi-naive evaluation and
stratified negation.  Pure standard-library Python.

Syntax
------
    fact(a, b).                       % ground facts
    edge(a, b) @ 3.                   % facts may carry a numeric weight
                                      % (ignored here; used by semiring.py)
    head(X) :- body(X, Y), not q(Y).  % rules; `not` is stratified negation
    % and # start line comments

Constants are lowercase identifiers, numbers (int or float), or quoted
strings.  Compound terms like s(N) are *parsed* but rejected by
validation — banning function symbols is precisely the restriction that
makes Datalog terminate.  For Horn clauses with function symbols, see the
top-down interpreter in prolog.py.
Variables start with an uppercase letter or underscore ('_' is anonymous).
`not` is reserved for negation.

Semantics
---------
* Safety: every variable in a rule head, and every variable in a negated
  body literal, must also appear in a positive body literal of that rule.
* Stratified negation: IDB predicates are partitioned into strata so that
  no predicate depends (directly or transitively) on its own negation.
  If negation occurs inside a recursive cycle, the program is rejected
  and the offending cycle is reported.
* Semi-naive evaluation: each stratum is evaluated to fixpoint; after the
  first round, recursive rules are re-evaluated only with the previous
  round's new facts (the "delta") substituted into each recursive body
  position in turn, instead of recomputing every join from scratch.
* Magic sets: with --magic, each query is answered by first rewriting the
  program (adornments + magic predicates, left-to-right sideways
  information passing) so that bottom-up evaluation only derives facts
  relevant to the query's bound arguments — goal-directed evaluation
  without giving up semi-naive.  Negated subgoals are not specialised:
  their predicates are included untransformed and computed in full, which
  keeps the rewriting stratified whenever the original program is.
  (Implementation: magic.py.)

Stratifiability is a *syntactic* condition; rejection by the stratified
engine does not by itself mean a program is semantically paradoxical.
For small programs, `--models` grounds the program and reports the
semantic story: all stable models (by exhaustive search) and the
well-founded (three-valued) model.  (Implementation: semantics.py.)

This file is the core: AST, parser, safety validation, stratification,
and the semi-naive evaluator, plus the CLI.  Lesson 12 of the course is
a guided tour of how it all works.

CLI
---
    python3 datalog.py program.dl               # print derived relations
    python3 datalog.py --trace program.dl       # + strata and per-round deltas
    python3 datalog.py -q 'eats_in_cafe(X)' program.dl
    python3 datalog.py --magic -q 'path(n5, X)' program.dl   # goal-directed
    python3 datalog.py --models program.dl      # stable + well-founded models
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Var:
    name: str

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class Const:
    value: object  # str or int

    def __str__(self):
        v = self.value
        if isinstance(v, str) and not re.fullmatch(r"[a-z][A-Za-z0-9_]*", v):
            return '"%s"' % v
        return str(v)


@dataclass(frozen=True)
class Struct:
    """A compound term like s(N) or cons(H, T).  Parsed for prolog.py's
    benefit; Datalog validation rejects it (the function-symbol ban)."""
    functor: str
    args: tuple

    def __str__(self):
        return "%s(%s)" % (self.functor, ", ".join(map(str, self.args)))


@dataclass(frozen=True)
class Atom:
    pred: str
    args: tuple

    def __str__(self):
        if not self.args:
            return self.pred
        return "%s(%s)" % (self.pred, ", ".join(map(str, self.args)))


@dataclass(frozen=True)
class Literal:
    atom: Atom
    negated: bool = False

    def __str__(self):
        return ("not " if self.negated else "") + str(self.atom)


@dataclass(frozen=True)
class Rule:
    head: Atom
    body: tuple  # tuple of Literal; empty tuple => fact
    weight: object = None   # numeric fact annotation `@ w`; facts only
    retract: bool = False   # `fact~.` — an update for incremental.py

    def __str__(self):
        if not self.body:
            if self.retract:
                return "%s~." % self.head
            if self.weight is not None:
                return "%s @ %s." % (self.head, self.weight)
            return "%s." % self.head
        return "%s :- %s." % (self.head, ", ".join(map(str, self.body)))


class DatalogError(Exception):
    pass


class ParseError(DatalogError):
    pass


class SafetyError(DatalogError):
    pass


class StratificationError(DatalogError):
    def __init__(self, message, cycle=None):
        super().__init__(message)
        self.cycle = cycle or []


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# One regex, alternatives tried in order, each wrapped in a named group —
# whichever group matched tells us the token kind.  Two orderings matter:
# `:-` must be tried somewhere `:` alone can't shadow it (there is no
# lone-colon token, so it's safe), and the number alternative must come
# before `dot`, so that in `edge(a, b) @ 3.5.` the "3.5" is one float
# token and the final "." still terminates the clause.
_TOKEN = re.compile(
    r"""
      (?P<ws>\s+)
    | (?P<comment>[%\#][^\n]*)
    | (?P<implies>:-)
    | (?P<lparen>\() | (?P<rparen>\)) | (?P<comma>,) | (?P<at>@)
    | (?P<retract>~)
    | (?P<number>-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)
    | (?P<dot>\.)
    | (?P<string>"[^"\n]*"|'[^'\n]*')
    | (?P<var>[A-Z_][A-Za-z0-9_]*)
    | (?P<ident>[a-z][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)


def _num(text):
    return float(text) if any(c in text for c in ".eE") else int(text)


def _tokenize(text):
    pos, line = 0, 1
    tokens = []
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise ParseError("line %d: unexpected character %r" % (line, text[pos]))
        kind = m.lastgroup
        value = m.group()
        if kind not in ("ws", "comment"):
            tokens.append((kind, value, line))
        line += value.count("\n")
        pos = m.end()
    tokens.append(("eof", "", line))
    return tokens


class _Parser:
    """Recursive descent over the token stream — one method per grammar
    rule, reading top to bottom:

        program := clause*
        clause  := atom [ '@' number ] '.'  |  atom ':-' literal (',' literal)* '.'
        literal := [ 'not' ] atom
        atom    := IDENT [ '(' term (',' term)* ')' ]
        term    := VARIABLE | NUMBER | STRING | IDENT [ '(' term... ')' ]

    The last alternative of `term` (an identifier with arguments) is a
    compound term like s(N) — parsed here so prolog.py can share this
    parser, but rejected later by Datalog validation."""

    def __init__(self, text):
        self.tokens = _tokenize(text)
        self.i = 0
        self.fresh = 0  # counter for renaming each `_` to a fresh variable

    def _peek(self):
        return self.tokens[self.i]

    def _next(self):
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def _expect(self, kind):
        tok = self._next()
        if tok[0] != kind:
            raise ParseError("line %d: expected %s, got %r" % (tok[2], kind, tok[1]))
        return tok

    def parse_program(self):
        clauses = []
        while self._peek()[0] != "eof":
            clauses.append(self._parse_clause())
        return clauses

    def _parse_clause(self):
        head = self._parse_atom()
        body = ()
        weight = None
        retract = False
        kind = self._peek()[0]
        if kind == "at":
            self._next()
            tok = self._expect("number")
            weight = _num(tok[1])
        elif kind == "retract":
            self._next()
            retract = True
        elif kind == "implies":
            self._next()
            lits = [self._parse_literal()]
            while self._peek()[0] == "comma":
                self._next()
                lits.append(self._parse_literal())
            body = tuple(lits)
        self._expect("dot")
        return Rule(head, body, weight, retract)

    def _parse_literal(self):
        kind, value, _line = self._peek()
        negated = False
        if kind == "ident" and value == "not":
            self._next()
            negated = True
        return Literal(self._parse_atom(), negated)

    def _parse_atom(self):
        tok = self._expect("ident")
        pred = tok[1]
        args = []
        if self._peek()[0] == "lparen":
            self._next()
            args.append(self._parse_term())
            while self._peek()[0] == "comma":
                self._next()
                args.append(self._parse_term())
            self._expect("rparen")
        return Atom(pred, tuple(args))

    def _parse_term(self):
        kind, value, line = self._next()
        if kind == "var":
            if value == "_":
                self.fresh += 1
                return Var("_G%d" % self.fresh)
            return Var(value)
        if kind == "ident":
            if self._peek()[0] == "lparen":
                self._next()
                args = [self._parse_term()]
                while self._peek()[0] == "comma":
                    self._next()
                    args.append(self._parse_term())
                self._expect("rparen")
                return Struct(value, tuple(args))
            return Const(value)
        if kind == "number":
            return Const(_num(value))
        if kind == "string":
            return Const(value[1:-1])
        raise ParseError("line %d: expected a term, got %r" % (line, value))


def parse(text):
    """Parse a Datalog program into a list of Rule (facts have empty body)."""
    return _Parser(text).parse_program()


# ---------------------------------------------------------------------------
# Validation: arity consistency, groundness of facts, rule safety
# ---------------------------------------------------------------------------

AGGREGATES = {"count", "sum", "min", "max"}


def _aggregate_of(atom):
    """The (index, functor, variable) of an aggregate term like sum(V) in
    a rule head, or None.  At most one aggregate per head."""
    found = None
    for i, a in enumerate(atom.args):
        if isinstance(a, Struct) and a.functor in AGGREGATES \
                and len(a.args) == 1 and isinstance(a.args[0], Var):
            if found is not None:
                raise SafetyError("at most one aggregate per head: %s" % atom)
            found = (i, a.functor, a.args[0])
    return found


def validate(clauses, arity=None):
    """Check arities, ground facts, and safety.  Returns {pred: arity}.
    An `arity` seed map lets a caller check new clauses against an
    already-loaded program's signature (incremental.py does this).
    "Safety" is range restriction, and it is what makes every relation
    finite: a variable may appear in a rule head, or under `not`, only if
    a positive body literal also binds it.  Without it, p(X) :- q(a)
    would assert p of *everything*, and `not r(X)` with X unbound would
    quantify over an open universe.  The compound-term check is the
    Datalog boundary itself — see the module docstring and prolog.py."""
    arity = dict(arity) if arity is not None else {}

    def check_arity(atom):
        n = arity.setdefault(atom.pred, len(atom.args))
        if n != len(atom.args):
            raise SafetyError(
                "predicate %s used with arity %d and %d" % (atom.pred, len(atom.args), n))

    def check_term(a, rule):
        if isinstance(a, Struct):
            raise SafetyError(
                "function symbols are not Datalog: term %s in %s.  "
                "Datalog bans compound terms so that bottom-up "
                "evaluation always terminates; for Horn clauses with "
                "function symbols use the top-down engine (prolog.py)."
                % (a, rule))

    for rule in clauses:
        check_arity(rule.head)
        # heads may carry one aggregate term, e.g. total(P, sum(A)); any
        # other compound term is the function-symbol boundary
        agg = _aggregate_of(rule.head)
        for i, a in enumerate(rule.head.args):
            if not (agg and i == agg[0]):
                check_term(a, rule)
        if agg and not rule.body:
            raise SafetyError("an aggregate needs a rule body: %s" % rule)
        if rule.weight is not None and rule.body:
            raise SafetyError("only facts may carry an @ weight: %s" % rule)
        for lit in rule.body:
            check_arity(lit.atom)
            for a in lit.atom.args:
                check_term(a, rule)
        if not rule.body:
            if any(isinstance(a, Var) for a in rule.head.args):
                raise SafetyError("fact is not ground: %s" % rule)
            continue
        positive_vars = {a.name for lit in rule.body if not lit.negated
                         for a in lit.atom.args if isinstance(a, Var)}
        head_vars = [a for a in rule.head.args if isinstance(a, Var)]
        if agg:
            head_vars.append(agg[2])   # the aggregated variable
        for a in head_vars:
            if a.name not in positive_vars:
                raise SafetyError(
                    "unsafe rule: head variable %s is not bound by a positive "
                    "body literal in: %s" % (a, rule))
        for lit in rule.body:
            if lit.negated:
                for a in lit.atom.args:
                    if isinstance(a, Var) and a.name not in positive_vars:
                        raise SafetyError(
                            "unsafe rule: variable %s of negated literal %s is not "
                            "bound by a positive literal in: %s" % (a, lit, rule))
    return arity


# ---------------------------------------------------------------------------
# Stratification
# ---------------------------------------------------------------------------

def _tarjan(nodes, edges):
    """Strongly connected components; returns {node: scc_id}.

    Why SCCs?  A program is stratifiable exactly when no *cycle* of
    dependencies contains a negative edge, and every cycle lives inside
    one SCC — so the whole check reduces to: does any negative edge have
    both endpoints in the same component?  This is Tarjan's algorithm in
    its iterative form (an explicit frame stack instead of recursion, so
    a long dependency chain can't hit Python's recursion limit)."""
    adj = defaultdict(list)
    for u, v, _neg in edges:
        adj[u].append(v)
    index, low, scc = {}, {}, {}
    stack, on_stack = [], set()
    counter = 0
    scc_id = 0
    for root in sorted(nodes):
        if root in index:
            continue
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        frames = [(root, iter(adj[root]))]
        while frames:
            node, it = frames[-1]
            advanced = False
            for child in it:
                if child not in index:
                    index[child] = low[child] = counter
                    counter += 1
                    stack.append(child)
                    on_stack.add(child)
                    frames.append((child, iter(adj[child])))
                    advanced = True
                    break
                elif child in on_stack:
                    low[node] = min(low[node], index[child])
            if advanced:
                continue
            frames.pop()
            if frames:
                parent = frames[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                sid = scc_id
                scc_id += 1
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc[w] = sid
                    if w == node:
                        break
    return scc


def _find_cycle(u, v, edges, sccs, first_kind):
    """Given a strict edge u -> v inside one SCC, return a cycle
    [(from, to, kind), ...] from u back to u through v."""
    sid = sccs[u]
    adj = defaultdict(list)
    for a, b, neg in edges:
        if sccs.get(a) == sid and sccs.get(b) == sid:
            adj[a].append((b, neg))
    prev = {v: None}
    queue = deque([v])
    while queue:
        n = queue.popleft()
        if n == u:
            break
        for b, neg in adj[n]:
            if b not in prev:
                prev[b] = (n, neg)
                queue.append(b)
    path = []
    n = u
    while prev[n] is not None:
        p, kind = prev[n]
        path.append((p, n, kind))
        n = p
    path.reverse()
    return [(u, v, first_kind)] + path


def _format_cycle(cycle):
    parts = [cycle[0][0]]
    for _u, v, kind in cycle:
        parts.append(" --> " if kind == "+" else " --%s--> " % kind)
        parts.append(v)
    return "".join(parts)


def stratify(clauses):
    """Assign a stratum (1-based int) to each IDB predicate.

    Raises StratificationError, with the offending cycle attached, if
    negation occurs inside a recursive cycle.
    """
    rules = [r for r in clauses if r.body]
    idb = {r.head.pred for r in rules}
    # Edges are labelled: "+" ordinary, "not" through negation, "agg"
    # into an aggregating rule.  Negation and aggregation both demand
    # "finish that relation completely before I look" — so both are
    # strict, and both are forbidden inside a cycle.
    edges = set()  # (head_pred, body_pred, kind): head depends on body
    for r in rules:
        aggregating = _aggregate_of(r.head) is not None
        for lit in r.body:
            if lit.atom.pred in idb:
                kind = ("not" if lit.negated
                        else "agg" if aggregating else "+")
                edges.add((r.head.pred, lit.atom.pred, kind))

    sccs = _tarjan(idb, edges)
    for (u, v, kind) in sorted(edges):
        if kind != "+" and sccs.get(u) == sccs.get(v):
            cycle = _find_cycle(u, v, edges, sccs, kind)
            what = ("aggregation" if any(k == "agg" for _a, _b, k in cycle)
                    else "negation")
            raise StratificationError(
                "program is not stratifiable — %s occurs inside a "
                "recursive cycle: %s.  No stratum assignment exists, so the "
                "program has no stratified model." % (what,
                                                     _format_cycle(cycle)),
                cycle=cycle)

    # Assign stratum numbers by relaxation: a predicate must sit at least
    # as high as anything it depends on, and *strictly* higher than
    # anything it depends on through negation ("compute that completely
    # before I ask what's not in it").  The SCC check above guarantees no
    # negative cycle, so these constraints have a finite solution and the
    # loop terminates at the least one.
    stratum = {p: 1 for p in idb}
    changed = True
    while changed:
        changed = False
        for (u, v, kind) in edges:
            need = stratum[v] + (0 if kind == "+" else 1)
            if stratum[u] < need:
                stratum[u] = need
                changed = True
    return stratum


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

_MISSING = object()
_EMPTY = frozenset()


def _match(args, tup, subst):
    """Extend subst so that args == tup, or return None.

    This is one-way unification (pattern matching): `tup` is always
    ground, so a variable either takes the tuple's value or must agree
    with its earlier binding, and a constant simply has to be equal.
    Joins fall out for free — matching path(X, Y) then edge(Y, Z) under
    one growing substitution *is* the join on Y."""
    s = dict(subst)
    for a, v in zip(args, tup):
        if isinstance(a, Const):
            if a.value != v:
                return None
        else:
            bound = s.get(a.name, _MISSING)
            if bound is _MISSING:
                s[a.name] = v
            elif bound != v:
                return None
    return s


class Program:
    def __init__(self, clauses):
        for c in clauses:
            if c.retract:
                raise SafetyError(
                    "retraction (%s) is an update, not a statement — a "
                    "static program simply wouldn't assert the fact.  "
                    "Apply it to a live materialisation via incremental.py."
                    % c)
        self.arity = validate(clauses)
        self.facts = [r for r in clauses if not r.body]
        self.rules = [r for r in clauses if r.body]
        self.idb = {r.head.pred for r in self.rules}
        self.strata = stratify(clauses)


class Engine:
    """Bottom-up, stratum-by-stratum semi-naive evaluator.

    Data representation, in full: `rels` maps each predicate name to a
    Python set of ground tuples — path -> {("a","b"), ("a","c")}.  That's
    the whole database.  Rules never delete (Datalog is monotone within a
    stratum), so evaluation is: grow these sets until one full pass adds
    nothing.  Strata are computed once, then processed in order, so by
    the time a negated literal is consulted its relation is finished."""

    def __init__(self, program, naive=False):
        self.program = program
        self.naive = naive            # True: skip the delta discipline
        self.rels = defaultdict(set)  # pred -> set of ground tuples
        self.stats = []               # per-stratum iteration statistics
        # derivation-order stamps: base facts 0, then one tick per
        # absorbed round — --explain uses these to build well-founded
        # derivation trees (a fact's premises always carry lower stamps)
        self.first_seen = {}
        self._stamp = 0

    def run(self):
        for fact in self.program.facts:
            tup = tuple(a.value for a in fact.head.args)
            self.rels[fact.head.pred].add(tup)
            self.first_seen.setdefault((fact.head.pred, tup), 0)
        by_stratum = defaultdict(list)
        for rule in self.program.rules:
            by_stratum[self.program.strata[rule.head.pred]].append(rule)
        for level in sorted(by_stratum):
            self._eval_stratum(level, by_stratum[level])
        return self.rels

    def _eval_stratum(self, level, rules):
        preds = {r.head.pred for r in rules}
        stat = {"stratum": level, "preds": sorted(preds), "iterations": []}
        self.stats.append(stat)
        if self.naive:
            self._eval_stratum_naive(rules, stat)
            return

        # Round 1: evaluate every rule of the stratum against the full db.
        delta = defaultdict(set)
        for rule in rules:
            for tup in self._produce(rule):
                if tup not in self.rels[rule.head.pred]:
                    delta[rule.head.pred].add(tup)
        self._absorb(delta, stat)

        # Recursive rules: a positive body literal names a stratum predicate.
        recursive = []
        for rule in rules:
            occs = [i for i, lit in enumerate(rule.body)
                    if not lit.negated and lit.atom.pred in preds]
            if occs:
                recursive.append((rule, occs))

        # Semi-naive rounds: substitute the previous round's delta into each
        # recursive position in turn; every other literal reads the full
        # (already-updated) relations, so no new derivation is missed and
        # nothing is recomputed from only-old facts.
        while delta:
            new_delta = defaultdict(set)
            for rule, occs in recursive:
                head = rule.head.pred
                for i in occs:
                    if not delta.get(rule.body[i].atom.pred):
                        continue
                    for tup in self._eval_rule(rule, delta_occ=i, delta=delta):
                        if tup not in self.rels[head]:
                            new_delta[head].add(tup)
            delta = new_delta
            self._absorb(delta, stat)

    def _eval_stratum_naive(self, rules, stat):
        """Naive evaluation: every rule against the whole database, every
        round, until nothing new appears — no delta discipline, so every
        already-known fact is re-derived every round.  Deliberately
        wasteful: run --naive --trace beside the default to watch
        semi-naive earn its name (Lesson 2)."""
        stat["produced"] = []   # total tuples derived per round
        while True:
            delta = defaultdict(set)
            produced = 0
            for rule in rules:
                for tup in self._produce(rule):
                    produced += 1
                    if tup not in self.rels[rule.head.pred]:
                        delta[rule.head.pred].add(tup)
            stat["produced"].append(produced)
            self._absorb(delta, stat)
            if not delta:
                return

    def _produce(self, rule):
        """All head tuples one rule derives right now (aggregate-aware)."""
        if _aggregate_of(rule.head):
            return self._eval_aggregate(rule)
        return self._eval_rule(rule)

    def _absorb(self, delta, stat):
        self._stamp += 1
        for pred, tuples in delta.items():
            self.rels[pred] |= tuples
            for t in tuples:
                self.first_seen.setdefault((pred, t), self._stamp)
        stat["iterations"].append(
            {p: len(ts) for p, ts in delta.items() if ts})

    def _rule_substitutions(self, rule, delta_occ=None, delta=None,
                            seed=None):
        """Every substitution satisfying the rule body (positives joined
        first — they bind; negatives filter afterwards, against fully
        computed lower strata).  If delta_occ is given, the positive
        literal at that body index reads from `delta` instead of the
        full relations — the semi-naive restriction.  A `seed`
        substitution pre-binds variables (--explain uses this)."""
        # Positives first (they bind variables), negatives filter afterwards.
        ordered = sorted(range(len(rule.body)),
                         key=lambda i: rule.body[i].negated)
        substs = [dict(seed) if seed else {}]
        for i in ordered:
            lit = rule.body[i]
            if not substs:
                return []
            if lit.negated:
                rel = self.rels.get(lit.atom.pred, _EMPTY)
                substs = [s for s in substs
                          if self._instantiate(lit.atom, s) not in rel]
            else:
                if delta_occ is not None and i == delta_occ:
                    rel = delta.get(lit.atom.pred, _EMPTY)
                else:
                    rel = self.rels.get(lit.atom.pred, _EMPTY)
                args = lit.atom.args
                new = []
                for s in substs:
                    for tup in rel:
                        m = _match(args, tup, s)
                        if m is not None:
                            new.append(m)
                substs = new
        return substs

    def _eval_rule(self, rule, delta_occ=None, delta=None):
        """Yield head tuples derivable from one rule."""
        for s in self._rule_substitutions(rule, delta_occ, delta):
            yield self._instantiate(rule.head, s)

    def _eval_aggregate(self, rule):
        """Aggregate rules — total(P, sum(A)) :- charge(P, C, A). — group
        the body's distinct *solutions* by the plain head arguments and
        fold the aggregate over each group.  Set semantics applies to
        solutions (rows), not to the aggregated values: two different
        charges of 50 sum to 100, and count gives the same answer
        whichever bound variable you name — matching SQL and Soufflé.
        Stratification has already guaranteed the body relations are
        complete (aggregation edges are strict, like negation), so one
        evaluation suffices."""
        idx, func, var = _aggregate_of(rule.head)
        groups = defaultdict(list)
        seen = set()
        for s in self._rule_substitutions(rule):
            witness = tuple(sorted(s.items()))
            if witness in seen:
                continue
            seen.add(witness)
            key = tuple(a.value if isinstance(a, Const) else s[a.name]
                        for j, a in enumerate(rule.head.args) if j != idx)
            groups[key].append(s[var.name])
        for key, values in groups.items():
            try:
                if func == "count":
                    agg = len(values)
                elif func == "sum":
                    agg = sum(values)
                elif func == "min":
                    agg = min(values)
                else:
                    agg = max(values)
            except TypeError:
                raise DatalogError(
                    "cannot %s over mixed or non-numeric values in: %s"
                    % (func, rule))
            out = list(key)
            out.insert(idx, agg)
            yield tuple(out)

    @staticmethod
    def _instantiate(atom, subst):
        return tuple(a.value if isinstance(a, Const) else subst[a.name]
                     for a in atom.args)


def run_program(text):
    """Parse, stratify, and evaluate a program; return the Engine."""
    engine = Engine(Program(parse(text)))
    engine.run()
    return engine


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _sort_key(tup):
    # numbers sort numerically (and before strings); strings sort as text
    return tuple((0, v) if isinstance(v, (int, float)) else (1, str(v))
                 for v in tup)


def _format_value(v):
    if isinstance(v, str) and re.fullmatch(r"[a-z][A-Za-z0-9_]*", v):
        return v
    if isinstance(v, (int, float)):
        return str(v)
    return '"%s"' % v


def format_atom(pred, tup):
    if not tup:
        return pred
    return "%s(%s)" % (pred, ", ".join(_format_value(v) for v in tup))


def format_fact(pred, tup):
    return format_atom(pred, tup) + "."


def _print_strata(program):
    levels = defaultdict(list)
    for pred, level in program.strata.items():
        levels[level].append("%s/%d" % (pred, program.arity[pred]))
    print("Stratification:")
    for level in sorted(levels):
        print("  stratum %d: %s" % (level, ", ".join(sorted(levels[level]))))


def _print_stats(engine):
    print("Naive evaluation:" if engine.naive else "Semi-naive evaluation:")
    for stat in engine.stats:
        print("  stratum %d (%s):" % (stat["stratum"], ", ".join(stat["preds"])))
        produced = stat.get("produced")
        for n, round_ in enumerate(stat["iterations"], 1):
            extra = ""
            if produced and n <= len(produced):
                extra = "   (%d tuples derived)" % produced[n - 1]
            if round_:
                deltas = ", ".join("+%d %s" % (c, p)
                                   for p, c in sorted(round_.items()))
                print("    round %d: %s%s" % (n, deltas, extra))
            else:
                print("    round %d: no new facts — fixpoint%s" % (n, extra))


def _atom_sort_key(atom):
    pred, args = atom
    return (pred, _sort_key(args))


def _format_atoms(atoms):
    return "  ".join(format_fact(p, t)
                     for p, t in sorted(atoms, key=_atom_sort_key))


def _print_models(clauses):
    """Report the semantic story: stable models and the well-founded model."""
    from semantics import ground_program, stable_models, well_founded
    try:
        stratify(clauses)
        print("Syntactic check: stratifiable.")
    except StratificationError as exc:
        print("Syntactic check: not stratifiable (%s)." % _format_cycle(exc.cycle))
        print("  (Syntactic only — an unstratifiable program may still have "
              "stable models.)")
    grounding = ground_program(clauses)
    facts = grounding[0]
    models = stable_models(clauses, grounding=grounding)
    if not models:
        print("Stable models: none — no consistent two-valued model exists.")
    else:
        print("Stable models: %d" % len(models))
        for i, m in enumerate(
                sorted(models, key=lambda m: _format_atoms(m - facts)), 1):
            print("  model %d: %s" % (i, _format_atoms(m - facts)
                                      or "(EDB facts only)"))
    true, undef = well_founded(clauses, grounding=grounding)
    print("Well-founded model (three-valued):")
    print("  true:      %s" % (_format_atoms(true - facts) or "(EDB facts only)"))
    print("  undefined: %s" % (_format_atoms(undef) or "(none)"))
    return 0


def parse_goal(q):
    """Parse a query/goal string into a single atom (no validation —
    prolog.py uses this too, and its goals may carry compound terms)."""
    clauses = parse(q if q.rstrip().endswith(".") else q + ".")
    if len(clauses) != 1 or clauses[0].body:
        raise ParseError("query must be a single atom: %r" % q)
    return clauses[0].head


def check_query_atom(atom, arity=None):
    """Datalog-side validation of a query atom: no compound terms, and
    arity agreement with the program when known.  The single home for
    these checks — the CLI, magic.py, and semiring.py all route here."""
    for a in atom.args:
        if isinstance(a, Struct):
            raise SafetyError(
                "function symbols are not Datalog: term %s in query %s "
                "(see prolog.py)" % (a, atom))
    if arity is not None and atom.pred in arity \
            and arity[atom.pred] != len(atom.args):
        raise SafetyError(
            "query %s has arity %d but %s is used with arity %d"
            % (atom, len(atom.args), atom.pred, arity[atom.pred]))


def _parse_query_atom(q, arity=None):
    atom = parse_goal(q)
    check_query_atom(atom, arity)
    return atom


def match_answers(atom, tuples):
    """The tuples matching a query atom: constants filter, variables bind."""
    return [tup for tup in tuples if _match(atom.args, tup, {}) is not None]


def _print_answers(atom, tuples, suffix=""):
    print("?- %s%s" % (atom, suffix))
    answers = sorted(tuples, key=_sort_key)
    for tup in answers:
        print("   " + format_fact(atom.pred, tup))
    print("   (%d answer%s)" % (len(answers), "" if len(answers) == 1 else "s"))


# ---------------------------------------------------------------------------
# --explain: derivation trees
# ---------------------------------------------------------------------------
# Ask the engine WHY it believes a fact.  The trick that keeps the tree
# well-founded: every fact carries a derivation-order stamp (Engine
# first_seen), and its first derivation necessarily used premises with
# strictly smaller stamps — so searching for a rule instance whose
# positive premises all precede the fact always succeeds and can never
# justify a fact by itself.

def _derivation_of(engine, pred, tup):
    """A (rule, premises) justification for a derived fact, where every
    positive premise strictly precedes it in derivation order; None for
    base facts.  premises is a list of (literal, ground_tuple)."""
    stamp = engine.first_seen.get((pred, tup), 0)
    for rule in engine.program.rules:
        if rule.head.pred != pred:
            continue
        if _aggregate_of(rule.head):
            group = _aggregate_group(engine, rule, tup)
            if group is not None:
                return rule, group
            continue
        seed = _match(rule.head.args, tup, {})
        if seed is None:
            continue
        for s in engine._rule_substitutions(rule, seed=seed):
            premises = [(lit, engine._instantiate(lit.atom, s))
                        for lit in rule.body]
            if all(engine.first_seen.get((lit.atom.pred, p), 0) < stamp
                   for lit, p in premises if not lit.negated):
                return rule, premises
    return None


def _aggregate_group(engine, rule, tup):
    """For an aggregate-rule head tuple, the group's contributing values
    (one per distinct body solution), presented as a pseudo-premise."""
    idx, func, var = _aggregate_of(rule.head)
    key = tuple(v for j, v in enumerate(tup) if j != idx)
    values = []
    seen = set()
    for s in engine._rule_substitutions(rule):
        witness = tuple(sorted(s.items()))
        if witness in seen:
            continue
        seen.add(witness)
        k = tuple(a.value if isinstance(a, Const) else s[a.name]
                  for j, a in enumerate(rule.head.args) if j != idx)
        if k == key:
            values.append(s[var.name])
    if not values:
        return None
    shown = ", ".join(str(v) for v in
                      sorted(values, key=lambda x:
                             (0, x) if isinstance(x, (int, float))
                             else (1, str(x))))
    return [("aggregate", "%s over %d body solution%s of %s: [%s]"
             % (func, len(values), "" if len(values) == 1 else "s", var,
                shown))]


def explain(engine, pred, tup, indent=0, shown=None, lines=None):
    """Build an indented derivation tree for one fact; returns the lines."""
    lines = [] if lines is None else lines
    shown = set() if shown is None else shown
    pad = "  " * indent
    label = format_atom(pred, tup)
    if (pred, tup) in shown:
        lines.append("%s%s   (derivation shown above)" % (pad, label))
        return lines
    derivation = _derivation_of(engine, pred, tup)
    if derivation is None:
        lines.append("%s%s   (base fact)" % (pad, label))
        return lines
    shown.add((pred, tup))
    rule, premises = derivation
    lines.append("%s%s   [via %s]" % (pad, label, rule))
    for item in premises:
        if item[0] == "aggregate":
            lines.append("%s  = %s" % (pad, item[1]))
        elif item[0].negated:
            lines.append("%s  not %s   (absent from its completed stratum)"
                         % (pad, format_atom(item[0].atom.pred, item[1])))
        else:
            explain(engine, item[0].atom.pred, item[1], indent + 1,
                    shown, lines)
    return lines


def _run_explain(q, engine):
    atom = _parse_query_atom(q, engine.program.arity)
    matches = sorted(match_answers(atom, engine.rels.get(atom.pred, ())),
                     key=_sort_key)
    print("?- explain %s" % atom)
    if not matches:
        print("   (no matching facts)")
        return
    for tup in matches:
        for line in explain(engine, atom.pred, tup):
            print("   " + line)


def _run_query(q, engine):
    atom = _parse_query_atom(q, engine.program.arity)
    _print_answers(atom, match_answers(atom, engine.rels.get(atom.pred, ())))


def _run_magic_query(q, clauses, trace):
    from magic import magic_transform
    atom = _parse_query_atom(q)
    transformed, answer_pred = magic_transform(clauses, atom)
    mprog = Program(transformed)
    mengine = Engine(mprog)
    if trace:
        print("Magic-sets rewriting (answer predicate %s):" % answer_pred)
        for c in transformed:
            print("  %s" % c)
        print()
        _print_strata(mprog)
        print()
    mengine.run()
    if trace:
        _print_stats(mengine)
        magic_total = sum(len(mengine.rels.get(p, ())) for p in mprog.idb)
        try:
            fengine = Engine(Program(clauses))
            fengine.run()
            full_total = sum(len(fengine.rels.get(p, ()))
                             for p in fengine.program.idb)
            print("[magic] %d IDB facts derived vs %d under full evaluation"
                  % (magic_total, full_total))
        except StratificationError:
            print("[magic] %d IDB facts derived (no full-evaluation baseline: "
                  "the original program is not stratifiable)" % magic_total)
        print()
    _print_answers(atom, match_answers(atom, mengine.rels.get(answer_pred, ())),
                   suffix="   [magic]")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="datalog.py",
        description="A small Datalog engine with semi-naive evaluation "
                    "and stratified negation.")
    ap.add_argument("file", help="Datalog program (.dl)")
    ap.add_argument("-t", "--trace", action="store_true",
                    help="print stratification and per-round delta statistics")
    ap.add_argument("-a", "--all", action="store_true",
                    help="print EDB (input) relations too, not just derived ones")
    ap.add_argument("-q", "--query", action="append", default=[], metavar="ATOM",
                    help="query, e.g. 'eats_in_cafe(X)' (repeatable)")
    ap.add_argument("-m", "--models", action="store_true",
                    help="skip stratified evaluation; instead ground the "
                         "program and report all stable models (exhaustive "
                         "search, small programs only) and the well-founded "
                         "three-valued model")
    ap.add_argument("--naive", action="store_true",
                    help="evaluate naively (no delta discipline); with "
                         "--trace, prints tuples-derived per round so the "
                         "semi-naive comparison is measurable")
    ap.add_argument("-e", "--explain", action="append", default=[],
                    metavar="ATOM",
                    help="print a derivation tree for every fact matching "
                         "the atom (repeatable)")
    ap.add_argument("-M", "--magic", action="store_true",
                    help="answer each -q query via the magic-sets rewriting "
                         "(goal-directed: only facts relevant to the query's "
                         "bound arguments are derived); with --trace, also "
                         "print the rewritten program and derivation counts")
    args = ap.parse_args(argv)

    with open(args.file) as fh:
        text = fh.read()

    try:
        # every mode re-validates via Program / magic_transform /
        # ground_program, so parsing is all that must happen up front
        clauses = parse(text)
    except DatalogError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    if args.models:
        try:
            return _print_models(clauses)
        except DatalogError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1

    if args.magic:
        if not args.query:
            print("error: --magic requires at least one -q/--query",
                  file=sys.stderr)
            return 1
        for q in args.query:
            try:
                _run_magic_query(q, clauses, args.trace)
            except StratificationError as exc:
                print("REJECTED: %s" % exc, file=sys.stderr)
                return 2
            except DatalogError as exc:
                print("error: %s" % exc, file=sys.stderr)
                return 1
        return 0

    try:
        program = Program(clauses)
    except StratificationError as exc:
        print("REJECTED: %s" % exc, file=sys.stderr)
        print("(This is a syntactic verdict.  Run with --models for the "
              "semantic one: stable models and the well-founded model.)",
              file=sys.stderr)
        return 2
    except DatalogError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    engine = Engine(program, naive=args.naive)
    if args.trace:
        _print_strata(program)
        print()
    engine.run()
    if args.trace:
        _print_stats(engine)
        print()

    if args.query or args.explain:
        for q in args.query:
            try:
                _run_query(q, engine)
            except DatalogError as exc:
                print("error: %s" % exc, file=sys.stderr)
                return 1
        for q in args.explain:
            try:
                _run_explain(q, engine)
            except DatalogError as exc:
                print("error: %s" % exc, file=sys.stderr)
                return 1
        return 0

    preds = sorted(set(program.arity) if args.all else program.idb)
    for pred in preds:
        tuples = engine.rels.get(pred, set())
        kind = "derived" if pred in program.idb else "input"
        print("%% %s/%d (%s) — %d fact%s" %
              (pred, program.arity[pred], kind, len(tuples),
               "" if len(tuples) == 1 else "s"))
        for tup in sorted(tuples, key=_sort_key):
            print(format_fact(pred, tup))
        print()
    return 0


if __name__ == "__main__":
    # Running as a script makes this module `__main__`, while the
    # satellite modules import it as `datalog`.  Without this aliasing,
    # Python loads a SECOND copy of the module, and isinstance checks
    # between the two copies' AST classes quietly fail — the classic
    # double-import trap (it made every CLI magic query look unbound).
    sys.modules["datalog"] = sys.modules["__main__"]
    sys.exit(main())
