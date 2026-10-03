"""tiny-datalog — a logic engine small enough to read in an afternoon.

The engine proper is `tiny_datalog.datalog`; the names below are its
public surface, re-exported here so that library use reads as

    from tiny_datalog import Engine, Program, parse

Everything else in the package is a satellite built on top of it:
`magic` (goal-directed rewriting), `semantics` (stable and well-founded
models), `semiring` (provenance-weighted evaluation), `incremental`
(maintenance under updates), `tabling` (top-down with memoing),
`subsumption` (KL-ONE style classification), `containment` (query
containment), `defeasible` (rules with exceptions and priorities), and
`prolog` (a Prolog reader for the same syntax).
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

__version__ = "0.1.2"

__all__ = [
    "Var", "Const", "Struct", "Atom", "Literal", "Rule",
    "DatalogError", "ParseError", "SafetyError", "StratificationError",
    "parse", "validate", "stratify", "parse_goal", "check_query_atom",
    "Program", "Engine", "run_program",
    "match_answers", "explain", "whynot",
    "format_atom", "format_fact",
    "__version__",
]
