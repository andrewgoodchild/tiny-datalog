"""tiny-datalog — a Datalog engine whose core you can read in an afternoon.

The package has three tiers.  `tiny_datalog.core` is the language —
AST, parser, validation, stratification — and `tiny_datalog.datalog` is
the base engine built on it, the bottom-up evaluator.  The names below
are their public surface, re-exported here so that library use reads as

    from tiny_datalog import Engine, Program, parse

`tiny_datalog.engines` lists the pluggable engines, which all give the
same answers: semi-naive and naive (`datalog`), `magic` (goal-directed
rewriting) and `tabling` (top-down with memoing).

Everything else is an extension built on the core, asking a different
question of a program: `semantics` (stable and well-founded models),
`semiring` (provenance-weighted evaluation), `incremental` (maintenance
under updates), `subsumption` (KL-ONE style classification),
`containment` (query containment), `defeasible` (rules with exceptions
and priorities), and `prolog` (a Prolog reader for the same syntax).
Import those by name: `from tiny_datalog import semiring`.
"""

from tiny_datalog.datalog import (
    # AST
    Var, Const, Struct, Atom, Literal, Rule,
    # errors
    DatalogError, ParseError, SafetyError, StratificationError,
    # front end
    parse, validate, stratify, parse_goal, check_query_atom,
    # evaluation
    Program, Engine, run_program,
    # answers and justification
    match_answers, explain, whynot,
    # formatting
    format_atom, format_fact,
)

__version__ = "0.3.0"

__all__ = [
    "Var", "Const", "Struct", "Atom", "Literal", "Rule",
    "DatalogError", "ParseError", "SafetyError", "StratificationError",
    "parse", "validate", "stratify", "parse_goal", "check_query_atom",
    "Program", "Engine", "run_program",
    "match_answers", "explain", "whynot",
    "format_atom", "format_fact",
    "__version__",
]
