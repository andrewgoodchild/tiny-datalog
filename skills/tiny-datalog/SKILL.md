---
name: tiny-datalog
description: Write and run Datalog programs with the tiny-datalog engine to answer questions that are recursive (reachability, closures, "at any depth"), rule-based (policies, eligibility, access), temporal (what held when), or that need a traceable derivation. Use when a question needs rules applied over more facts than fit in context, when an answer must be explained or audited, or when an agent should keep facts it was told and derive conclusions from them instead of re-reasoning in prose.
---

# tiny-datalog

A Datalog engine: you state facts and rules, it derives every
consequence, and it can say why any answer holds or does not. Pure
Python, no dependencies. From a checkout, `python3 datalog.py`; after
`pip install tiny-datalog`, the same CLI is `tiny-datalog`.

## The loop

1. **Write facts and rules to a `.dl` file.** Facts are what you were
   told or measured. Rules are how conclusions follow. Keep them apart:
   never write a conclusion down as a fact.
2. **Run it, and read stderr first.** Warnings mean a legal program
   that is probably wrong (see below). Fix them before reading answers.
3. **Query** with `-q 'pred(X, const)'`.
4. **Before trusting or reporting an answer, explain it**:
   `--explain 'pred(a, b)'`. Quote the derivation, not your own
   summary of it. For a *missing* answer, explain the ground atom
   anyway: you get each rule's first failing literal.
5. **State the properties that must hold as constraints** (`:- body.`)
   and check the exit status (3 means one was violated).
6. **Report from the engine's output.** Answers, counterexamples and
   derivations are the evidence.

```sh
python3 datalog.py program.dl                      # every derived relation
python3 datalog.py -q 'path(a, X)' program.dl      # answers to a query
python3 datalog.py --explain 'path(a, d)' program.dl   # why / why not
python3 datalog.py --assume 'edge(d, a).' -q 'path(a, X)' program.dl   # what if?
python3 datalog.py --assume 'edge(a, b)~.' program.dl  # what if this fact were gone?
python3 datalog.py --models program.dl             # is the rule set coherent?
```

Exit status: 0 fine, 1 error (message on stderr), 2 not stratifiable,
3 a constraint was violated (the rest of the output is still printed).

## Syntax

```prolog
edge(a, b).                          % fact: lowercase constants
person("Ann Lee").                   % quote anything that is not a lowercase identifier
due(loan1, "2024-03-01").            % ISO dates as strings compare as dates
path(X, Y) :- edge(X, Y).            % rule: uppercase variables, comma is "and"
path(X, Z) :- edge(X, Y), path(Y, Z).   % recursion
free(P) :- person(P), not busy(P).   % stratified negation
late(L) :- due(L, D), today(T), D < T.   % comparisons: < <= > >= = !=
total(P, sum(A)) :- charge(P, _, A). % aggregates in the head: count sum min max
:- path(X, X).                       % constraint: this must never hold
```

`%` starts a comment. `_` is a fresh anonymous variable. Several rules
with the same head mean "or".

## Gotchas

- **Capitalised words are variables.** `works_at(Alice, acme)` asks
  about everyone. Write `alice`, or `"Alice"`.
- **Safety.** Every variable in the head, under `not`, or in a
  comparison must also appear in a positive body literal. `late(L) :-
  due(L, D), D < T.` is refused: say what `T` is (`today(T)`).
- **No arithmetic.** There is no `+`. Comparisons check values and
  never make them. Use aggregates, or precompute values as facts.
- **Negate one thing.** `not overdue(P, B)` with `B` unused elsewhere is
  refused. Project first: `has_overdue(P) :- overdue(P, _).`
- **Negation cannot go through recursion.** The engine names the cycle.
  `--models` gives the stable-model reading if you need one.
- **Ordering a number against a string is an error.** `=` and `!=`
  between them are just false and true.
- **Values are one visible token.** Strings may not contain line
  breaks, control characters, invisible characters, or both kinds of
  quote, so text from a document cannot break out of a value in the
  output you read back.
  Store an id and keep the text elsewhere.

## Warnings to act on (stderr)

- `no fact or rule defines p/1, so it is empty (did you mean q?)`:
  almost always a typo. Under `not`, a typo makes the condition always
  true, which fails open.
- `p can never hold: every rule for it needs p first`: missing base
  case.
- `... cannot all hold, so this rule can never fire`: contradictory
  comparisons, often a wrong variable in an interval test.

## Patterns

- **Facts that stop being true:** keep every statement with its date,
  `said(Subject, Relation, Object, Date)`. A later statement about a
  one-value relation supersedes the earlier one. Derive the current
  state; never delete history. See `lessons/23-time.md` and
  `programs/employment.dl`.
- **Memory with provenance:** add the source (episode, document, line)
  as an argument of each stated fact. `--explain` then ends at the
  source. See `lessons/24-memory.md` and `programs/memory.dl`.
- **Contradictions:** write them as constraints, not as rules that pick
  a winner. A violated constraint is a question to ask the user.
- **Abstain honestly:** zero answers means the facts do not support
  the claim. Say "not known", and explain the ground atom to show what
  is missing.
- **Cost and confidence:** weight facts with `@ w` and run
  `semiring.py --semiring minplus|viterbi|why` (positive programs).

## Python

```python
from tiny_datalog import run_program, explain, parse
from tiny_datalog.core import lint

engine = run_program(rules_text, facts={"said": rows})   # rows: tuples of str/int/float
engine.query("current(user, R, O)")      # [{'R': ..., 'O': ...}, ...]
engine.violations()                      # [(constraint, [substitution, ...]), ...]
explain(engine, "current", ("user", "manager", "dana"))   # list of lines
lint(parse(rules_text))                  # the CLI's warnings
```
