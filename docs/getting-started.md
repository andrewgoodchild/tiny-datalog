# Getting started

Everything is one file of standard-library Python — there is nothing to
install beyond Python 3.9+.

```sh
git clone <this repo>
cd datalog
python3 tests.py                     # 32 tests, should all pass
python3 datalog.py programs/reachability.dl
```

## Running programs

A program is a plain-text `.dl` file of facts and rules:

```prolog
% comments start with % (or #)
parent(abe, bob).                        % a fact
ancestor(X, Y) :- parent(X, Y).          % a rule
ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z).
```

Save that as `family.dl` and run it:

```sh
python3 datalog.py family.dl
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

engine = run_program(open("family.dl").read())
print(engine.rels["ancestor"])           # set of tuples

query = parse("ancestor(bob, X).")[0].head
_, answers = magic_query(parse(open("family.dl").read()), query)
```

## Where to go next

The lessons build up the whole engine feature by feature:

1. [Facts, rules, and queries](01-first-steps.md)
2. [Recursion and semi-naive evaluation](02-recursion.md)
3. [Negation and stratification](03-negation.md)
4. [Magic sets: asking questions efficiently](04-magic-sets.md)
5. [Beyond stratification: stable models and the café paradox](05-beyond-stratification.md)
