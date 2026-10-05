"""
core.py — what every part of tiny-datalog shares: the language itself.
Pure standard-library Python.

The package is built in three tiers:

* the **core** (this file): the AST, the parser, safety validation,
  stratification, one-way matching, value formatting, query helpers and
  the small pieces of command-line plumbing every CLI uses.  It defines
  what a Datalog program *is*, and evaluates nothing.
* the **engines**: interchangeable evaluation strategies that give the
  same answers to the same stratified program — semi-naive and naive
  bottom-up (datalog.py, the base engine), magic sets (magic.py) and
  tabling (tabling.py).  engines.py names them and states their shared
  interface.
* the **extensions**: modules that ask a *different* question of a
  program, and so give different answers on purpose — stable and
  well-founded models (semantics.py), semiring weights (semiring.py),
  maintenance under updates (incremental.py), defeasible logic
  (defeasible.py), Prolog with function symbols (prolog.py), concept
  subsumption (subsumption.py) and query containment (containment.py).

Every engine and extension imports from here; nothing here imports
them.

Syntax
------
    fact(a, b).                       % ground facts
    edge(a, b) @ 3.                   % facts may carry a numeric weight
                                      % (ignored by datalog.py; used by
                                      % semiring.py)
    head(X) :- body(X, Y), not q(Y).  % rules; `not` is stratified negation
    % and # start line comments

Constants are lowercase identifiers, numbers (int or float), or quoted
strings.  Compound terms like s(N) are *parsed* but rejected by
validation — banning function symbols is precisely the restriction that
makes Datalog terminate.  For Horn clauses with function symbols, see the
top-down interpreter in prolog.py.
Variables start with an uppercase letter or underscore ('_' is anonymous).
`not` is reserved for negation.

The two static checks
---------------------
* Safety: every variable in a rule head, and every variable in a negated
  body literal, must also appear in a positive body literal of that rule.
* Stratified negation: IDB predicates are partitioned into strata so that
  no predicate depends (directly or transitively) on its own negation.
  If negation occurs inside a recursive cycle, the program is rejected
  and the offending cycle is reported.

The Under the hood sections of lessons 1-3 are a guided tour of this
file and of the evaluator in datalog.py.
"""

from __future__ import annotations

import functools
import math
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
        return "_" if self.anonymous else self.name

    @property
    def anonymous(self):
        """True for a renamed `_`.  The parser names each one `_#1`, `_#2`,
        ...: '#' starts a comment, so no variable a user writes can have
        that name, and none can collide with it.  (prolog.py's renamings
        append '#n', so a renamed `_` still starts '_#' and a renamed X,
        as 'X#3', still prints as itself.)"""
        return self.name.startswith("_#")


@dataclass(frozen=True)
class Const:
    value: object  # str or int

    def __str__(self):
        return _format_value(self.value)


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
    | (?P<number>-?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)
    | (?P<dot>\.)
    | (?P<string>"[^"\n]*"|'[^'\n]*')
    | (?P<var>[A-Z_][A-Za-z0-9_]*)
    | (?P<ident>[a-z][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)


def _num(text, line):
    n = float(text) if any(c in text for c in ".eE") else int(text)
    if isinstance(n, float) and not math.isfinite(n):
        # 1e400 would become inf, which prints as a constant named inf
        raise ParseError("line %d: number %s is too large" % (line, text))
    return n


def _shown(tok):
    """A token as an error message quotes it."""
    return "end of input" if tok[0] == "eof" else repr(tok[1])


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
            raise ParseError("line %d: expected %s, got %s"
                             % (tok[2], kind, _shown(tok)))
        return tok

    def _comma_list(self, parse_item):
        """item (`,` item)* — the grammar's one list shape, shared by a
        rule body (literals) and an argument list (terms)."""
        items = [parse_item()]
        while self._peek()[0] == "comma":
            self._next()
            items.append(parse_item())
        return items

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
            weight = _num(tok[1], tok[2])
        elif kind == "retract":
            self._next()
            retract = True
        elif kind == "implies":
            self._next()
            body = tuple(self._comma_list(self._parse_literal))
        self._expect("dot")
        return Rule(head, body, weight, retract)

    def _parse_literal(self):
        kind, value, line = self._peek()
        negated = False
        if kind == "ident" and value == "not":
            self._next()
            negated = True
            if self._peek()[0] == "lparen":
                raise ParseError("line %d: `not` is negation, not a predicate "
                                 "— write `not p(X)`" % line)
        return Literal(self._parse_atom(), negated)

    def _parse_atom(self):
        tok = self._expect("ident")
        pred = tok[1]
        if pred == "not":
            raise ParseError("line %d: `not` is reserved for negation and "
                             "cannot name a predicate" % tok[2])
        args = []
        if self._peek()[0] == "lparen":
            self._next()
            args = self._comma_list(self._parse_term)
            self._expect("rparen")
        return Atom(pred, tuple(args))

    def _parse_term(self):
        tok = self._next()
        kind, value, line = tok
        if kind == "var":
            if value == "_":
                self.fresh += 1
                return Var("_#%d" % self.fresh)   # see Var.anonymous
            return Var(value)
        if kind == "ident":
            if value == "not":
                raise ParseError("line %d: `not` is reserved for negation; "
                                 "write the constant as \"not\"" % line)
            if self._peek()[0] == "lparen":
                self._next()
                args = self._comma_list(self._parse_term)
                self._expect("rparen")
                return Struct(value, tuple(args))
            return Const(value)
        if kind == "number":
            return Const(_num(value, line))
        if kind == "string":
            return Const(value[1:-1])
        raise ParseError("line %d: expected a term, got %s"
                         % (line, _shown(tok)))


def parse(text):
    """Parse a Datalog program into a list of Rule (facts have empty body)."""
    return _Parser(text).parse_program()


# ---------------------------------------------------------------------------
# Validation: arity consistency, groundness of facts, rule safety
# ---------------------------------------------------------------------------

AGGREGATES = {"count", "sum", "min", "max"}


def aggregate_of(atom):
    """The (index, functor, variable) of an aggregate term like sum(V) in
    a rule head, or None.  At most one aggregate per head.  Every module
    that must treat aggregate rules specially — the evaluator, magic
    sets, tabling, the extensions — asks this one function."""
    found = None
    for i, a in enumerate(atom.args):
        if isinstance(a, Struct) and a.functor in AGGREGATES \
                and len(a.args) == 1 and isinstance(a.args[0], Var):
            if found is not None:
                raise SafetyError("at most one aggregate per head: %s" % atom)
            found = (i, a.functor, a.args[0])
    return found


# The name this had while it was private to datalog.py; kept so that
# code written against the old name still imports.
_aggregate_of = aggregate_of


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
        agg = aggregate_of(rule.head)
        for i, a in enumerate(rule.head.args):
            if not (agg and i == agg[0]):
                check_term(a, rule)
        if agg and not rule.body:
            raise SafetyError("an aggregate needs a rule body: %s" % rule)
        # unreachable from parse() — the grammar's `@ weight` and `:- body`
        # are exclusive branches — but validate() is the checkpoint for
        # clauses a caller assembled directly, and semiring.py silently
        # skips weighted rules rather than failing on them
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
        aggregating = aggregate_of(r.head) is not None
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
# Matching: one-way unification
# ---------------------------------------------------------------------------

_MISSING = object()
_EMPTY = frozenset()


def match(args, tup, subst):
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


# The name this had while it was private to datalog.py; kept so that
# code written against the old name still imports.
_match = match


# ---------------------------------------------------------------------------
# Facts from Python data
# ---------------------------------------------------------------------------

_PREDICATE = re.compile(r"[a-z][A-Za-z0-9_]*\Z")


def python_facts(facts):
    """{predicate: rows} as fact clauses (see datalog.run_program)."""
    clauses = []
    for pred, rows in facts.items():
        if not isinstance(pred, str) or not _PREDICATE.match(pred) \
                or pred == "not":
            raise DatalogError("%r cannot name a predicate: a predicate is "
                               "a lowercase identifier" % (pred,))
        for row in rows:
            if not isinstance(row, (tuple, list)):
                row = (row,)
            for v in row:
                # bool is an int in Python, and would print as a constant
                # named True; nan and inf print as constants too
                if (isinstance(v, bool) or not isinstance(v, (str, int, float))
                        or (isinstance(v, float) and not math.isfinite(v))):
                    raise DatalogError(
                        "fact %s%r: values must be str, int or finite float, "
                        "not %r" % (pred, tuple(row), v))
            clauses.append(Rule(Atom(pred, tuple(Const(v) for v in row)), ()))
    return clauses


# ---------------------------------------------------------------------------
# Values: sorting and formatting
# ---------------------------------------------------------------------------

def sort_key(tup):
    """The key every printed listing sorts a tuple of values by, so that
    output is stable from run to run."""
    # numbers sort numerically (and before strings); strings sort as text
    return tuple((0, v) if isinstance(v, (int, float)) else (1, str(v))
                 for v in tup)


# The name this had while it was private to datalog.py; kept so that
# code written against the old name still imports.
_sort_key = sort_key


def _format_value(v):
    """A value as source text that parses back to it: bare identifiers
    stay bare, anything else is quoted — with single quotes if it
    contains a double one.  (The lexer has no escapes, so a string with
    both kinds of quote cannot be written, and so never needs printing.)"""
    if isinstance(v, str) and re.fullmatch(r"[a-z][A-Za-z0-9_]*", v) \
            and v != "not":
        return v
    if isinstance(v, (int, float)):
        return str(v)
    return "'%s'" % v if '"' in v else '"%s"' % v


def format_atom(pred, tup):
    if not tup:
        return pred
    return "%s(%s)" % (pred, ", ".join(_format_value(v) for v in tup))


def format_fact(pred, tup):
    return format_atom(pred, tup) + "."


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def parse_goal(q):
    """Parse a query/goal string into a single atom (no validation —
    prolog.py uses this too, and its goals may carry compound terms).
    The final '.' is optional; it is added as a token, not as text, so
    that a trailing `% comment` cannot swallow it."""
    parser = _Parser(q)
    tokens = parser.tokens
    if len(tokens) > 1 and tokens[-2][0] != "dot":
        tokens.insert(-1, ("dot", ".", tokens[-1][2]))
    clauses = parser.parse_program()
    if len(clauses) != 1 or clauses[0].body:
        raise ParseError("query must be a single atom: %r" % q)
    if clauses[0].weight is not None or clauses[0].retract:
        raise ParseError("a query is a plain atom — no @ weight or ~ "
                         "retraction: %r" % q)
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


def parse_query_atom(q, arity=None):
    """Query text as a checked Datalog query atom: parse_goal, then
    check_query_atom against the program's `arity` map when given.
    Every CLI that takes -q goes through here."""
    atom = parse_goal(q)
    check_query_atom(atom, arity)
    return atom


# The name this had while it was private to datalog.py; kept so that
# code written against the old name still imports.
_parse_query_atom = parse_query_atom


def match_answers(atom, tuples):
    """The tuples matching a query atom: constants filter, variables bind."""
    return [tup for tup in tuples if match(atom.args, tup, {}) is not None]


# ---------------------------------------------------------------------------
# Command-line plumbing shared by every CLI
# ---------------------------------------------------------------------------

def read_program(path):
    """Read a program file, reporting the everyday mistakes — a typo in
    the name, a directory, an unreadable file — as a DatalogError, which
    every CLI here already knows how to print.  Without this they escape
    as a traceback, which tells a reader nothing they can act on."""
    try:
        with open(path) as fh:
            return fh.read()
    except OSError as exc:
        raise DatalogError("cannot read %s: %s"
                           % (path, exc.strerror or exc))
    except UnicodeDecodeError:
        raise DatalogError("cannot read %s: not text (a binary file?)"
                           % path)


def cli(main):
    """Decorate a command-line ``main`` so that any DatalogError escaping
    it is reported the same way everywhere: one line, ``error: ...``, on
    stderr, and exit status 1.  A user's mistake — a typo in the program,
    a missing file, an unsafe rule — is not a bug in the engine, so it
    deserves a sentence, not a traceback.  (argparse's own usage errors
    exit with status 2 before ``main`` gets this far, and are untouched.)
    Every CLI in the package wears this, so each ``main`` only spells out
    the cases that are *not* the generic one."""
    @functools.wraps(main)
    def wrapper(argv=None):
        try:
            return main(argv)
        except DatalogError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
    return wrapper
