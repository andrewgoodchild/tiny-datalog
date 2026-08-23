# Getting started

Everything is one file of standard-library Python — there is nothing to
install beyond Python 3.9+.

```sh
git clone https://github.com/<you>/tiny-datalog
cd tiny-datalog
python3 tests.py                     # 119 tests, should all pass
python3 datalog.py programs/02-reachability.dl
```

## Running programs

A program is a plain-text `.dl` file of facts and rules:

```prolog
% comments start with % (or #)
parent(abe, bob).                        % a fact
ancestor(X, Y) :- parent(X, Y).          % a rule
ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z).
```

Save that as `01-family.dl` and run it:

```sh
python3 datalog.py 01-family.dl
```

The engine prints every *derived* relation (add `--all` to also print the
input facts). The other modes:

| Command | What it does |
|---|---|
| `python3 datalog.py prog.dl` | evaluate, print derived relations |
| `python3 datalog.py -q 'ancestor(abe, X)' prog.dl` | evaluate, answer a query |
| `python3 datalog.py --magic -q '...' prog.dl` | answer the query *goal-directedly* (magic sets) |
| `python3 datalog.py --trace prog.dl` | show strata and per-round derivation counts |
| `python3 datalog.py --models prog.dl` | stable models + well-founded model (small programs) |
| `python3 datalog.py --naive --trace prog.dl` | naive evaluation with per-round derivation counts |
| `python3 datalog.py --explain 'path(a, d)' prog.dl` | print a derivation tree — *why* is this fact true? |
| `python3 tabling.py prog.dl -q 'goal(X)' -t` | tabled top-down evaluation (handles left recursion) |
| `python3 incremental.py prog.dl -u 'f(a)~. f(b).'` | apply retractions/insertions to a live materialisation |
| `python3 semiring.py --semiring minplus prog.dl` | evaluate over a semiring (costs, counts, provenance, probabilities) |
| `python3 incremental.py` | demo: repair derived facts on insert/delete instead of recomputing |
| `python3 prolog.py prog.pl -q 'goal(X)'` | top-down Horn clauses *with* function symbols |
| `python3 subsumption.py ontology.dl` | classify a KL-ONE-style ontology (compiled to Datalog) |
| `python3 containment.py prog.dl` | minimise conjunctive queries; `--contains` tests containment |

## Syntax reference

- **Constants**: lowercase identifiers (`bob`), integers (`42`), quoted
  strings (`"Mary Jane"`).
- **Variables**: start with an uppercase letter (`X`, `Cook`); `_` is an
  anonymous variable.
- **Facts** end with `.` and must be ground (no variables).
- **Rules**: `head :- literal, literal, ... .` Every literal is an atom or
  `not atom`. `not` is the negation keyword (and is reserved).
- **Safety**: every variable in a rule's head, and every variable under
  `not`, must also appear in a positive body literal.
- Zero-arity atoms are fine: `rainy.` and `wet :- rainy.`

## Using it from Python

```python
from datalog import run_program, parse, magic_query

engine = run_program(open("01-family.dl").read())
print(engine.rels["ancestor"])           # set of tuples

query = parse("ancestor(bob, X).")[0].head
_, answers = magic_query(parse(open("01-family.dl").read()), query)
```

## Where to go next

The lessons build up the whole repository feature by feature:

0. [What is Datalog, and why should you care?](00-what-is-datalog.md) —
   start here if Datalog is new to you: what it is, its history, and why
   it matters in the LLM era
1. [Facts, rules, and queries](01-first-steps.md)
2. [Recursion and semi-naive evaluation](02-recursion.md)
3. [Negation and stratification](03-negation.md)
4. [Magic sets: asking questions efficiently](04-magic-sets.md)
5. [Beyond stratification: stable models and the café paradox](05-beyond-stratification.md)
6. [Semirings: provenance and recursive aggregation](06-semirings.md)
7. [Probabilistic Datalog, honestly](07-probabilistic.md)
8. [Incremental maintenance: don't recompute the world](08-incremental.md)
9. [Horn clauses: the boundary Datalog lives on](09-horn-clauses.md)
10. [KL-ONE and subsumption: reasoning about definitions](10-kl-one-subsumption.md)
11. [Under the hood: how this engine is built](11-under-the-hood.md)
12. [Aggregation: counting without contradiction](12-aggregation.md)
13. [Tabling: top-down without the cliff](13-tabling.md)
14. [Containment: the same search, one level up](14-containment.md)
15. [Closed and open worlds](15-closed-and-open-worlds.md)
