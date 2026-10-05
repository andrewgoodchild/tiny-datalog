"""
engines.py — the pluggable evaluation strategies, behind one interface.

The package has three tiers (core.py's docstring describes them).  This
file is the middle one made explicit: four algorithms that answer the
*same* question — what follows from a stratified program? — and must
therefore give identical answers.  They differ only in how much work
they do and in which order:

    seminaive   bottom-up, re-joining only the last round's new facts
                (datalog.py — the base engine, and the reference)
    naive       bottom-up, re-joining everything every round
                (datalog.py --naive)
    magic       rewrite the program for the query, then run it
                bottom-up (magic.py — Lesson 7)
    tabling     top-down with a table of answers per subgoal
                (tabling.py — Lesson 15)

The interface, which every entry of ENGINES follows:

    engine = ENGINES[name](clauses)   # clauses: a list of Rule, as from
                                      # core.parse; raises DatalogError
                                      # (StratificationError included)
                                      # if the program cannot be run
    engine.answers(atom)              # -> set of ground tuples matching
                                      #    a query Atom
    ENGINES[name].handles(clauses)    # -> False if this strategy cannot
                                      #    run the program at all

Every engine requires a *stratified* program — that is what makes their
answers comparable — and refuses another one with StratificationError.
`handles` is for the narrower, per-engine gaps: tabling has no
aggregation, so it says False to a program with an aggregate rule.

Because the answers must agree, the registry doubles as a test oracle:
tests.py (ConformanceTests, DifferentialFuzzTests) and
conformance/run.py run every program through every engine that handles
it and demand the semi-naive answer from each.  `datalog.py --engine
NAME -q ATOM` picks one from the command line.

The extensions (semantics, semiring, incremental, defeasible, prolog,
subsumption, containment) are deliberately not here: they ask other
questions — other semantics, weighted answers, updates, a different
logic — so "same answers as semi-naive" is not their contract.
"""

from __future__ import annotations

from tiny_datalog.core import aggregate_of, stratify, validate
from tiny_datalog.datalog import Engine, Program
from tiny_datalog.magic import magic_query
from tiny_datalog.tabling import TabledEngine


class SemiNaive:
    """Bottom-up semi-naive evaluation: materialise every relation once,
    then answer each query by lookup.  The reference engine."""

    naive = False

    @staticmethod
    def handles(clauses):
        return True

    def __init__(self, clauses):
        self.engine = Engine(Program(clauses), naive=self.naive)
        self.engine.run()

    def answers(self, atom):
        return self.engine.answers(atom)


class Naive(SemiNaive):
    """Bottom-up naive evaluation: the same fixpoint, reached by re-running
    every rule against the whole database each round (Lesson 2)."""

    naive = True


class Magic:
    """Magic sets: rewrite the program for each query so that bottom-up
    evaluation derives only facts relevant to it, then run semi-naive on
    the rewritten program.  Aggregate predicates are computed in full."""

    @staticmethod
    def handles(clauses):
        return True

    def __init__(self, clauses):
        # check up front what the other engines check on construction:
        # the rewriting itself would quietly run an unstratified program
        # whose unstratified part a particular query never reaches
        validate(clauses)
        stratify(clauses)
        self.clauses = list(clauses)

    def answers(self, atom):
        # magic_transform checks the query atom against the program
        _engine, answers = magic_query(self.clauses, atom)
        return answers


class Tabling:
    """Tabled top-down evaluation (iterative QSQR): one table of answers
    per subgoal, grown to fixpoint.  No aggregation."""

    @staticmethod
    def handles(clauses):
        return not any(c.body and aggregate_of(c.head) for c in clauses)

    def __init__(self, clauses):
        self.engine = TabledEngine(clauses)

    def answers(self, atom):
        return self.engine.query(atom)


# name -> engine class; insertion order is the order tests and the CLI
# list them, reference first
ENGINES = {
    "seminaive": SemiNaive,
    "naive": Naive,
    "magic": Magic,
    "tabling": Tabling,
}
