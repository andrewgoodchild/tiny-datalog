#!/usr/bin/env python3
"""
defeasible.py — defeasible logic: rules with exceptions and priorities.
(Lesson 18, which ends with a tour of this module.)

Lesson 3 met defaults through `not`: birds fly unless abnormal.  That
works for one exception, written by hand into the rule it overrides.
Real rule sets — statutes, policies, eligibility criteria — are made of
generalisations, exceptions to them, exceptions to the exceptions, and
an order saying which wins.  Defeasible logic (Nute, 1994) makes all of
that first-class:

    r1: penguin(X) -> bird(X).        % strict: no exceptions, ever
    r2: bird(X) => flies(X).          % defeasible: usually
    r3: penguin(X) => ~flies(X).      % a rule for the opposite
    r4: injured(X) ~> ~flies(X).      % a defeater: can only block
    r3 > r2.                          % superiority: r3 beats r2

`~` is *strong* negation — `~flies(opus)` is a claim, not an absence —
and a conflict is exactly a pair of complementary literals.  There is
no `not` here at all: exceptions are rules that attack, priorities say
who wins, and an unresolved conflict yields neither side instead of
whichever rule happened to have the `not` written into it.

Conclusions carry four tags (Antoniou, Billington, Governatori & Maher
2001):

    +Δ q   q is definitely provable: facts and strict rules alone
    −Δ q   q is demonstrably not definitely provable
    +∂ q   q is defeasibly provable: some applicable rule supports q,
           ~q is not definite, and every rule for ~q is either
           inapplicable or beaten by an applicable rule for q
    −∂ q   q is demonstrably not defeasibly provable

"Demonstrably": a −tag is a finite proof of failure, not the mere
absence of a +tag.  On a loop like `a => b. b => a.` neither +∂ b nor
−∂ b is ever established, and the module reports b as *undecided* —
where Lesson 5's well-founded semantics would settle it false, as does
the well-founded variant of this logic (Maher & Governatori 1999).
Standard defeasible logic is characterised instead by Kunen's
three-valued semantics of a logic program that encodes the theory —
which is why it cannot see that such a loop has no foundation.

The proof conditions are implemented one-to-one in `_conclude`, over
the theory's grounding, as a fixpoint: tags are only ever added, so
iteration stops.  Grounding reuses the core engine.  Every rule, read
as if strict, is a positive Datalog rule, and its least model bounds
everything a +tag could be about; see `Theory.ground` for the one
consequence of grounding that way.  `--propagating` switches from
ambiguity blocking to ambiguity propagation (`programs/ambiguity.dfl`
shows the difference).
"""

import argparse
import re
import sys
from collections import defaultdict
from itertools import combinations

from tiny_datalog.datalog import (
    Atom, DatalogError, Engine, Literal, ParseError, Program, Rule,
    SafetyError, Var, format_atom, match_answers, parse_goal, read_program,
    _sort_key)

STRICT, DEFEASIBLE, DEFEATER = "->", "=>", "~>"

_TOKEN = re.compile(r"""
    (?P<comment>%[^\n]*) | (?P<space>\s+)
  | (?P<string>"[^"\n]*"|'[^'\n]*')
  | (?P<number>-?[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)
  | (?P<arrow>->|=>|~>) | (?P<punct>[:,.()>~])
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
""", re.VERBOSE)


def complement(lit):
    """`p` <-> `~p`.  A literal is (pred, args); strong negation lives
    in the predicate name, so the core engine stores ~p as a relation
    of its own and never needs to know it is special."""
    pred, args = lit
    return (pred[1:] if pred.startswith("~") else "~" + pred), args


def show(lit):
    return format_atom(*lit)


class Theory:
    """A parsed defeasible theory: facts, labelled rules, superiority."""

    def __init__(self):
        self.facts = []         # core Atoms; a ~ fact has pred "~p"
        self.rules = []         # (label, kind, head Atom, body Atoms)
        self.superior = set()   # (stronger label, weaker label)

    # -- reading ------------------------------------------------------------

    @classmethod
    def parse(cls, text):
        theory = cls()
        tokens = _tokens(text)
        statement = []
        for tok in tokens:
            statement.append(tok)
            if tok[1] == "." and _depth(statement) == 0:
                theory._statement(statement[:-1], tok[2])
                statement = []
        if statement:
            raise ParseError("line %d: expected '.', got end of input"
                             % statement[-1][2])
        theory._check()
        return theory

    def _statement(self, toks, line):
        text = [t[1] for t in toks]
        if len(toks) == 3 and text[1] == ">":           # r3 > r2.
            self.superior.add((text[0], text[2]))
            return
        label = None
        if len(toks) > 1 and toks[0][0] == "name" and text[1] == ":":
            label, toks = text[0], toks[2:]
        arrows = [i for i, t in enumerate(toks) if t[0] == "arrow"]
        if not arrows:
            if label is not None:
                raise ParseError("line %d: a labelled statement must be a "
                                 "rule (->, => or ~>)" % line)
            self.facts.append(_atom(toks, line))
            return
        if len(arrows) > 1:
            raise ParseError("line %d: one arrow per rule" % line)
        i = arrows[0]
        body = [_atom(part, line) for part in _split(toks[:i])]
        head = _atom(toks[i + 1:], line)
        self.rules.append((label or "_r%d" % (len(self.rules) + 1),
                           toks[i][1], head, tuple(_fresh_anonymous(body))))

    def _check(self):
        labels = [r[0] for r in self.rules]
        dup = {l for l in labels if labels.count(l) > 1}
        if dup:
            raise ParseError("rule label used twice: %s" % ", ".join(sorted(dup)))
        for pair in self.superior:
            for l in pair:
                if l not in labels:
                    raise ParseError("superiority names unknown rule %s" % l)
        # the superiority relation must be acyclic, or "r beats s"
        # could end up meaning r beats itself
        beats = defaultdict(set)
        for a, b in self.superior:
            beats[a].add(b)
        for start in list(beats):
            stack, seen = list(beats[start]), set()
            while stack:
                x = stack.pop()
                if x == start:
                    raise SafetyError("superiority is cyclic through %s"
                                      % start)
                if x not in seen:
                    seen.add(x)
                    stack.extend(beats[x])

    # -- grounding ----------------------------------------------------------

    def ground(self):
        """Ground rules (label, kind, head, body) over literals, and the
        set of facts.

        Every rule is first read as a strict positive Datalog rule; the
        core engine's least model of that program — the *envelope* —
        holds every literal any rule could ever establish.  A rule
        instance is kept when its variables can all be bound by body
        literals inside the envelope; the body literals it does not
        match there simply fail.  So `p, q => r` with q underivable is
        kept, and r is refuted (−∂) as the proof theory says, while an
        instance no derivable literal could bind at all is never made.

        That is the one place this departs from the proof theory, which
        ranges over every constant.  A loop nothing starts, written with
        variables — `a(X) => b(X). b(X) => a(X).` — is not reported at
        all, where the proof theory would leave each instance undecided.
        Written without variables it needs no binding, is kept, and
        comes out undecided (`programs/loops.dfl`)."""
        rules = [Rule(head, tuple(Literal(b, False) for b in body))
                 for _l, _k, head, body in self.rules]
        program = Program([Rule(a, ()) for a in self.facts] + rules)
        arities = defaultdict(set)
        for pred, n in program.arity.items():
            arities[pred.lstrip("~")].add(n)
        for pred, ns in sorted(arities.items()):
            if len(ns) > 1:
                raise SafetyError("predicate %s used with arities %s (its "
                                  "negation counts too)"
                                  % (pred, " and ".join(map(str, sorted(ns)))))
        engine = Engine(program)
        engine.run()
        facts = {(a.pred, tuple(x.value for x in a.args)) for a in self.facts}
        ground, seen = [], set()
        for label, kind, head, body in self.rules:
            needed = _variables(body)
            # match every subset of the body that binds all variables
            for n in range(len(body) + 1):
                for part in combinations(body, n):
                    if _variables(part) != needed:
                        continue
                    sub = Rule(head, tuple(Literal(b, False) for b in part))
                    for subst in engine._rule_substitutions(sub):
                        g = (label, kind,
                             (head.pred, engine._instantiate(head, subst)),
                             tuple((b.pred, engine._instantiate(b, subst))
                                   for b in body))
                        if g not in seen:
                            seen.add(g)
                            ground.append(g)
        return facts, ground

    # -- the proof theory ---------------------------------------------------

    def conclusions(self, policy="blocking"):
        """{tag: set of literals} for the tags +Δ, −Δ, +∂, −∂, and
        'undecided' for literals that got neither +∂ nor −∂."""
        if policy not in ("blocking", "propagating"):
            raise DatalogError("unknown policy %r: use 'blocking' or "
                               "'propagating'" % (policy,))
        facts, ground = self.ground()
        return _conclude(facts, ground, self.superior, policy)


def _tokens(text):
    """(kind, text, line) triples; comments and whitespace dropped."""
    tokens, pos = [], 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if m is None:
            raise ParseError("line %d: unexpected character %r"
                             % (text.count("\n", 0, pos) + 1, text[pos]))
        if m.lastgroup not in ("space", "comment"):
            tokens.append((m.lastgroup, m.group(),
                           text.count("\n", 0, pos) + 1))
        pos = m.end()
    return tokens


def _variables(atoms):
    return {a.name for atom in atoms for a in atom.args if isinstance(a, Var)}


def _depth(toks):
    return sum({"(": 1, ")": -1}.get(t[1], 0) for t in toks)


def _split(toks):
    """Comma-separated parts at bracket depth 0."""
    parts, cur, depth = [], [], 0
    for t in toks:
        depth += {"(": 1, ")": -1}.get(t[1], 0)
        if t[1] == "," and depth == 0:
            parts.append(cur)
            cur = []
        else:
            cur.append(t)
    return parts + [cur] if cur else parts


def _atom(toks, line):
    """`[~] atom` -> core Atom, pred prefixed '~' when negated.  The atom
    itself goes through the core parser, so constants, strings,
    variables and its error messages are the ones the course knows."""
    if not toks:
        raise ParseError("line %d: expected a literal" % line)
    neg = toks[0][1] == "~"
    toks = toks[1:] if neg else toks
    if not toks or toks[0][0] != "name" or toks[0][1][0].isupper():
        raise ParseError("line %d: expected a literal, got %r"
                         % (line, " ".join(t[1] for t in toks) or "nothing"))
    atom = parse_goal(" ".join(t[1] for t in toks))
    return Atom(("~" if neg else "") + atom.pred, atom.args)


def _fresh_anonymous(atoms):
    """Each literal was parsed on its own, so each numbered its `_`s from
    1; renumber so two `_` in one rule stay two different variables."""
    n = 0
    out = []
    for a in atoms:
        args = []
        for x in a.args:
            if isinstance(x, Var) and x.anonymous:
                n += 1
                x = Var("_#%d" % n)
            args.append(x)
        out.append(Atom(a.pred, tuple(args)))
    return out


def _conclude(facts, ground, superior, policy):
    """The proof conditions, as a fixpoint (Antoniou, Billington,
    Governatori & Maher 2001).  For a literal q, R[q] is every rule for
    q, Rs[q] the strict ones, Rsd[q] strict or defeasible — defeaters
    may attack, never support — and A(r) is rule r's body:

      +Δq  q is a fact, or some r in Rs[q] has A(r) all +Δ.
      −Δq  q is not a fact, and every r in Rs[q] has some a in A(r) −Δ.
      +∂q  +Δq; or (1) some r in Rsd[q] has A(r) all +∂, (2) ~q is −Δ,
           and (3) every attacker s in R[~q] is either dead — some a in
           A(s) is −∂ — or beaten: some t in Rsd[q] with A(t) all +∂
           and t > s.  The t may differ per attacker: team defeat.
      −∂q  −Δq, and: every r in Rsd[q] has some a in A(r) −∂; or ~q is
           +Δ; or some attacker s in R[~q] is live — A(s) all +∂ — and
           every t in Rsd[q] has a body literal −∂ or is not above s.

    That is ambiguity *blocking*: an attacker only counts once its body
    is proved.  Under ambiguity *propagation* (Maher 2012) the same
    conditions hold with attackers judged by mere *support*, σ:

      +σq  +Δq, or some r in Rsd[q] has A(r) all +σ, and no attacker
           s in R[~q] with no −∂ body literal is above r.
      −σq  −Δq, and every r in Rsd[q] has a body literal −σ, or is
           below some attacker s in R[~q] with A(s) all +∂.

    and in +∂ an attacker is dead only if a body literal is −σ, while in
    −∂ it is live as soon as A(s) is all +σ.  Supported-but-unproved
    attackers then still block, so doubt spreads downstream."""
    by_head = defaultdict(list)
    for rule in ground:
        by_head[rule[2]].append(rule)
    # report on every literal the theory mentions; decide its complement
    # too, since every +∂ / −∂ condition looks at ~q
    mentioned = set(facts) | set(by_head) | {a for r in ground for a in r[3]}
    universe = mentioned | {complement(q) for q in mentioned}

    def strict(q):
        return [r for r in by_head[q] if r[1] == STRICT]

    def supporting(q):
        return [r for r in by_head[q] if r[1] != DEFEATER]

    def body_in(r, tagged):
        return all(a in tagged for a in r[3])

    def body_hits(r, tagged):
        return any(a in tagged for a in r[3])

    def above(t, s):
        return (t[0], s[0]) in superior

    plus_d, minus_d = set(), set()       # +Δ, −Δ: the strict part first
    changed = True
    while changed:
        changed = False
        for q in universe:
            if q not in plus_d and (q in facts or any(
                    body_in(r, plus_d) for r in strict(q))):
                plus_d.add(q)
                changed = True
            if q not in minus_d and q not in facts and all(
                    body_hits(r, minus_d) for r in strict(q)):
                minus_d.add(q)
                changed = True

    plus, minus = set(), set()           # +∂, −∂
    if policy == "propagating":
        s_plus, s_minus = set(), set()   # +σ, −σ: who is merely supported
    else:
        s_plus, s_minus = plus, minus    # blocking: support = proof
    changed = True
    while changed:
        changed = False
        for q in universe:
            nq = complement(q)
            attackers = by_head[nq]
            if q not in plus and (q in plus_d or (
                    any(body_in(r, plus) for r in supporting(q))
                    and nq in minus_d
                    and all(body_hits(s, s_minus) or any(
                        body_in(t, plus) and above(t, s)
                        for t in supporting(q)) for s in attackers))):
                plus.add(q)
                changed = True
            if q not in minus and q in minus_d and (
                    all(body_hits(r, minus) for r in supporting(q))
                    or nq in plus_d
                    or any(body_in(s, s_plus) and all(
                        body_hits(t, minus) or not above(t, s)
                        for t in supporting(q)) for s in attackers)):
                minus.add(q)
                changed = True
            if policy != "propagating":
                continue
            if q not in s_plus and (q in plus_d or any(
                    body_in(r, s_plus) and all(
                        body_hits(s, minus) or not above(s, r)
                        for s in attackers)
                    for r in supporting(q))):
                s_plus.add(q)
                changed = True
            if q not in s_minus and q in minus_d and all(
                    body_hits(r, s_minus) or any(
                        body_in(s, plus) and above(s, r) for s in attackers)
                    for r in supporting(q)):
                s_minus.add(q)
                changed = True
    return {"+Δ": plus_d & mentioned, "−Δ": minus_d & mentioned,
            "+∂": plus & mentioned, "−∂": minus & mentioned,
            "undecided": mentioned - plus - minus}


def load(text):
    return Theory.parse(text)


TAG_NAMES = [("+Δ", "definitely"), ("+∂", "defeasibly"),
             ("−∂", "not defeasibly"), ("undecided", "undecided")]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Defeasible logic: strict rules (->), defeasible rules "
                    "(=>), defeaters (~>), superiority (r1 > r2).")
    ap.add_argument("file", help="defeasible theory")
    ap.add_argument("-q", "--query", action="append", default=[],
                    metavar="LITERAL",
                    help="show the tags of matching literals (repeatable), "
                         "e.g. -q 'flies(X)' or -q '~flies(X)'")
    ap.add_argument("--propagating", action="store_true",
                    help="ambiguity propagating instead of blocking")
    args = ap.parse_args(argv)
    try:
        theory = load(read_program(args.file))
        result = theory.conclusions(
            "propagating" if args.propagating else "blocking")
        queries = [_atom(_tokens(q.rstrip(". ")), 1) for q in args.query]
    except DatalogError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    def ordered(lits):
        return sorted(lits, key=lambda l: (l[0].lstrip("~"), l[0],
                                           _sort_key(l[1])))

    if queries:
        for q in queries:
            print("?- %s" % (q.pred if not q.args else "%s(%s)" % (
                q.pred, ", ".join(str(a) for a in q.args))))
            hits = [l for l in ordered(set().union(*result.values()))
                    if l[0] == q.pred and match_answers(q, [l[1]])]
            for lit in hits:
                tags = [t for t, _n in TAG_NAMES if lit in result[t]]
                print("   %-28s %s" % (show(lit), "  ".join(tags)))
            if not hits:
                print("   (no rule or fact mentions it)")
        return 0
    for tag, name in TAG_NAMES:
        lits = ordered(result[tag])
        print("%s %s (%d)" % (tag, name, len(lits)) if tag != "undecided"
              else "%s (%d)" % (name, len(lits)))
        for lit in lits:
            print("   " + show(lit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
