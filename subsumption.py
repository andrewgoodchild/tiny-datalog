#!/usr/bin/env python3
"""
subsumption.py — KL-ONE-style concept subsumption, compiled to Datalog.
(Lesson 10; implementation tour in Lesson 11.)

KL-ONE (Brachman, late 1970s) organised knowledge as *concepts* with
structured definitions, and its party trick was the classifier: state
what a Father is, and the system *discovers* where Father belongs in the
concept hierarchy.  The reasoning service underneath is **subsumption**:
C is subsumed by D (written C ⊑ D) iff every possible instance of C must
be an instance of D — a statement about definitions, not about any
particular database.

This module implements subsumption for the EL concept language —
conjunction and existential restriction — by the standard
completion-rule calculus.  EL is the tractable core that the
SNOMED-scale reasoners (ELK, Snorocket) are built on; they implement
its extensions (EL++/ELH: top, bottom, role hierarchies, right
identities), which SNOMED CT actually requires and this module does
not.  See "Where this stops", below.  The twist that earns it a place in this
repository: after normalisation, the completion rules are *literally a
positive Datalog program*, and this module simply compiles the ontology
to facts + five rules and hands them to the engine from datalog.py.
Classification is a fixpoint; goal-directed subsumption checks even work
under magic sets.  (`--emit` prints the compiled Datalog so you can run
it yourself.)

Ontology syntax (parsed with the repository's own parser — concept
expressions are the compound terms Datalog itself forbids):

    isa(man, person).                       % primitive: necessary only
    define(parent, and(person, some(has_child, person))).
                                            % defined: necessary AND
                                            % sufficient — classifiable
    role(has_child).                        % optional declaration

Expressions: atomic names, and(...) with two or more conjuncts, and
some(role, expression).  The predicates subs, link, concept, isa1, isa2,
isa_some, some_isa are reserved for the compilation.

Normalisation introduces fresh names (gen_1, gen_2, ...) for nested
complex expressions — one inclusion per fresh name, direction chosen by
which side of ⊑ the expression sits on.  This is a conservative
extension: subsumptions among the *named* concepts are unchanged.

Where this stops
----------------
Plain EL, and nothing beyond it.  There is no ⊤ (so no "every concept
is subsumed by Thing"), no ⊥ or disjointness (so no unsatisfiable
concepts — this classifier cannot tell you a definition is
contradictory), no role hierarchies (`subrole/2` is rejected rather
than ignored), no role chains or right identities, no nominals, no
datatypes, and no ABox: it reasons about definitions only, never about
individuals.  The completion-rule *method* extends to all of that —
that is exactly how EL++ reasoners are built — but these five rules
are complete only for what is listed above.
"""

from __future__ import annotations

import argparse
import sys

from datalog import (Atom, Const, DatalogError, Engine, Literal, Program,
                     Rule, Struct, Var, parse)

_RESERVED = {"subs", "link", "concept", "isa1", "isa2", "isa_some",
             "some_isa"}


class Ontology:
    """An EL TBox, normalised on load into the four axiom forms:

        isa1(A, B)         A ⊑ B
        isa2(A1, A2, B)    A1 ⊓ A2 ⊑ B
        isa_some(A, r, B)  A ⊑ ∃r.B
        some_isa(r, A, B)  ∃r.A ⊑ B
    """

    def __init__(self):
        self.isa1 = []
        self.isa2 = []
        self.isa_some = []
        self.some_isa = []
        self.concepts = set()   # every atomic name, fresh ones included
        self.named = set()      # concepts the user actually named
        self.roles = set()
        self.told = set()       # (sub, super) pairs stated syntactically
        self._memo = {}         # normalised expression -> fresh name
        self._fresh = 0
        self._supers = None     # classification cache

    # -- loading ------------------------------------------------------------

    @classmethod
    def from_text(cls, text):
        ont = cls()
        for clause in parse(text):
            if clause.body:
                raise DatalogError(
                    "an ontology contains only facts, not rules: %s" % clause)
            pred, args = clause.head.pred, clause.head.args
            if pred == "isa" and len(args) == 2:
                ont._axiom(args[0], args[1], told=True)
            elif pred == "define" and len(args) == 2:
                if not isinstance(args[0], Const):
                    raise DatalogError(
                        "define/2 needs an atomic concept name: %s" % clause)
                # A definition is an equivalence: both inclusions.
                ont._axiom(args[0], args[1], told=True)
                ont._axiom(args[1], args[0])
            elif pred == "role" and len(args) == 1:
                ont.roles.add(ont._role_name(args[0]))
            elif pred == "primitive" and len(args) == 1:
                ont._concept_name(args[0])
            else:
                raise DatalogError(
                    "unknown ontology statement %s/%d (expected isa/2, "
                    "define/2, role/1, or primitive/1): %s"
                    % (pred, len(args), clause))
        return ont

    # -- names --------------------------------------------------------------

    def _concept_name(self, term):
        if not isinstance(term, Const) or not isinstance(term.value, str):
            raise DatalogError("expected an atomic concept name, got %s" % (term,))
        if term.value in _RESERVED:
            raise DatalogError(
                "%r is reserved by the compilation" % term.value)
        self.concepts.add(term.value)
        self.named.add(term.value)
        return term.value

    def _role_name(self, term):
        if not isinstance(term, Const) or not isinstance(term.value, str):
            raise DatalogError("expected an atomic role name, got %s" % (term,))
        self.roles.add(term.value)
        return term.value

    def _gen(self):
        self._fresh += 1
        name = "gen_%d" % self._fresh
        self.concepts.add(name)   # fresh names are concepts, but not named
        return name

    # -- normalisation ------------------------------------------------------
    #
    # The direction of each fresh-name inclusion follows the expression's
    # side of ⊑.  On the right (A ⊑ ...expr...) the fresh name goes BELOW
    # the expression; on the left (...expr... ⊑ B) it goes ABOVE.  Either
    # way the extension is conservative — a model may always interpret the
    # fresh name as exactly the expression.

    @staticmethod
    def _conjuncts(expr):
        # flatten nested and(...)s into one list
        if isinstance(expr, Struct) and expr.functor == "and":
            out = []
            for a in expr.args:
                out.extend(Ontology._conjuncts(a))
            return out
        return [expr]

    def _axiom(self, lhs, rhs, told=False):
        """Assert lhs ⊑ rhs for arbitrary expressions."""
        if isinstance(lhs, Const):
            self._sub_atom_expr(self._concept_name(lhs), rhs, told=told)
        elif isinstance(rhs, Const):
            self._sub_expr_atom(lhs, self._concept_name(rhs))
        else:
            mid = self._gen()          # Ĉ ⊑ D̂  →  Ĉ ⊑ A, A ⊑ D̂
            self._sub_expr_atom(lhs, mid)
            self._sub_atom_expr(mid, rhs)

    def _sub_atom_expr(self, a, expr, told=False):
        """a ⊑ expr, a atomic."""
        if isinstance(expr, Const):
            b = self._concept_name(expr)
            self.isa1.append((a, b))
            if told:
                self.told.add((a, b))
        elif isinstance(expr, Struct) and expr.functor == "and":
            for c in self._conjuncts(expr):
                self._sub_atom_expr(a, c, told=told)
        elif isinstance(expr, Struct) and expr.functor == "some" \
                and len(expr.args) == 2:
            r = self._role_name(expr.args[0])
            self.isa_some.append((a, r, self._below(expr.args[1])))
        else:
            raise DatalogError("not an EL concept expression: %s" % (expr,))

    def _sub_expr_atom(self, expr, b):
        """expr ⊑ b, b atomic."""
        if isinstance(expr, Const):
            self.isa1.append((self._concept_name(expr), b))
        elif isinstance(expr, Struct) and expr.functor == "and":
            atoms = [self._above(c) for c in self._conjuncts(expr)]
            # binarise a1 ⊓ a2 ⊓ a3 ⊑ b through fresh intermediates
            while len(atoms) > 2:
                t = self._gen()
                self.isa2.append((atoms[0], atoms[1], t))
                atoms = [t] + atoms[2:]
            if len(atoms) == 1:
                self.isa1.append((atoms[0], b))
            else:
                self.isa2.append((atoms[0], atoms[1], b))
        elif isinstance(expr, Struct) and expr.functor == "some" \
                and len(expr.args) == 2:
            r = self._role_name(expr.args[0])
            self.some_isa.append((r, self._above(expr.args[1]), b))
        else:
            raise DatalogError("not an EL concept expression: %s" % (expr,))

    def _below(self, expr):
        """Atomic name for expr in a right-hand position (name ⊑ expr)."""
        if isinstance(expr, Const):
            return self._concept_name(expr)
        key = ("below", str(expr))
        if key not in self._memo:
            self._memo[key] = a = self._gen()
            self._sub_atom_expr(a, expr)
        return self._memo[key]

    def _above(self, expr):
        """Atomic name for expr in a left-hand position (expr ⊑ name)."""
        if isinstance(expr, Const):
            return self._concept_name(expr)
        key = ("above", str(expr))
        if key not in self._memo:
            self._memo[key] = a = self._gen()
            self._sub_expr_atom(expr, a)
        return self._memo[key]

    # -- compilation to Datalog ---------------------------------------------

    def datalog(self):
        """The completion calculus as a Datalog program (AST clauses).

        Facts encode the normalised TBox; the five rules are the EL
        completion rules (CR1–CR4 plus reflexivity).  subs(C, D) in the
        fixpoint means C ⊑ D."""
        def atom(pred, *names):
            return Atom(pred, tuple(Const(n) for n in names))

        clauses = [Rule(atom("concept", c), ()) for c in sorted(self.concepts)]
        clauses += [Rule(atom("isa1", a, b), ()) for a, b in self.isa1]
        clauses += [Rule(atom("isa2", a1, a2, b), ())
                    for a1, a2, b in self.isa2]
        clauses += [Rule(atom("isa_some", a, r, b), ())
                    for a, r, b in self.isa_some]
        clauses += [Rule(atom("some_isa", r, a, b), ())
                    for r, a, b in self.some_isa]

        C, D, D1, D2, Dp, E, R = (Var(n) for n in
                                  ("C", "D", "D1", "D2", "Dp", "E", "R"))
        lit = lambda pred, *args: Literal(Atom(pred, tuple(args)))
        clauses += [
            # every concept subsumes itself
            Rule(Atom("subs", (C, C)), (lit("concept", C),)),
            # CR1: climb told inclusions
            Rule(Atom("subs", (C, E)),
                 (lit("subs", C, D), lit("isa1", D, E))),
            # CR2: two subsumers combine through a conjunction axiom
            Rule(Atom("subs", (C, E)),
                 (lit("subs", C, D1), lit("subs", C, D2),
                  lit("isa2", D1, D2, E))),
            # CR3: a subsumer with an existential creates a role link
            Rule(Atom("link", (C, R, E)),
                 (lit("subs", C, D), lit("isa_some", D, R, E))),
            # CR4: a role link whose target is subsumed appropriately
            Rule(Atom("subs", (C, E)),
                 (lit("link", C, R, D), lit("subs", D, Dp),
                  lit("some_isa", R, Dp, E))),
        ]
        return clauses

    def emit(self):
        """The compiled program as Datalog text — runnable by datalog.py."""
        return "\n".join(str(c) for c in self.datalog()) + "\n"

    # -- classification -----------------------------------------------------

    def classify(self):
        """{named concept: set of named strict subsumers}."""
        if self._supers is None:
            engine = Engine(Program(self.datalog()))
            engine.run()
            self._supers = {c: set() for c in self.named}
            for sub, sup in engine.rels["subs"]:
                if sub in self.named and sup in self.named and sub != sup:
                    self._supers[sub].add(sup)
        return self._supers

    def direct_subsumers(self):
        """The transitive reduction of classify(): for each concept, its
        immediate parents in the discovered hierarchy."""
        supers = self.classify()
        out = {}
        for c, sup in supers.items():
            out[c] = {d for d in sup
                      if not any(e != d and d in supers[e] and e not in supers[d]
                                 for e in sup)}
        return out

    def equivalences(self):
        supers = self.classify()
        return sorted({tuple(sorted((c, d)))
                       for c, sup in supers.items()
                       for d in sup if c in supers[d]})


def load(text):
    return Ontology.from_text(text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="subsumption.py",
        description="Classify an EL ontology by compiling subsumption "
                    "to Datalog.")
    ap.add_argument("file", help="ontology file (isa/2, define/2 facts)")
    ap.add_argument("-q", "--query", action="append", default=[],
                    metavar="CONCEPT",
                    help="print all subsumers of one concept (repeatable)")
    ap.add_argument("--emit", action="store_true",
                    help="print the compiled Datalog program and exit")
    args = ap.parse_args(argv)

    with open(args.file) as fh:
        text = fh.read()
    try:
        ont = load(text)
        if args.emit:
            sys.stdout.write(ont.emit())
            return 0
        supers = ont.classify()
        direct = ont.direct_subsumers()
    except DatalogError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    if args.query:
        for c in args.query:
            if c not in supers:
                print("error: unknown concept %r" % c, file=sys.stderr)
                return 1
            names = sorted(supers[c]) or ["(none)"]
            print("%s  ⊑  %s" % (c, ", ".join(names)))
        return 0

    told = ont.told
    inferred = 0
    print("Classification (%d named concepts):" % len(supers))
    for c in sorted(direct):
        if not direct[c]:
            print("  %-14s (top of hierarchy)" % c)
            continue
        parts = []
        for d in sorted(direct[c]):
            if (c, d) in told:
                parts.append(d)
            else:
                parts.append(d + "*")
                inferred += 1
        print("  %-14s ⊑  %s" % (c, ", ".join(parts)))
    for c, d in ont.equivalences():
        print("  %-14s ≡  %s" % (c, d))
    if inferred:
        print("  (* = inferred by the classifier, not stated)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
