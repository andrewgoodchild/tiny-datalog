# Getting started

Everything is one file of standard-library Python — there is nothing to
install beyond Python 3.9+.

```sh
git clone https://github.com/andrewgoodchild/tiny-datalog
cd tiny-datalog
python3 tests.py                     # 123 tests, should all pass
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

engine = run_program(open("family.dl").read())
print(engine.rels["ancestor"])           # set of tuples

query = parse("ancestor(bob, X).")[0].head
_, answers = magic_query(parse(open("family.dl").read()), query)
```

## Where to go next

Hit a word you don't know? [glossary.md](glossary.md) defines every
technical term the course uses, with the lesson that introduces it.


The lessons build up the whole repository feature by feature. The
numbers are file identifiers, not a mandatory order: a course covering
nine techniques has no single true sequence, so the paths below are the
routes worth taking.

**Start here, in order.** Lessons 1, 2 and 3 are the spine and
everything else assumes them: facts and rules, recursion, negation.

**Then pick a path.**

| If you are here to... | Read |
|---|---|
| write rules for a real policy | 12 (aggregation), 15 (missing data), 16 (authoring) |
| understand how evaluation works | 2, 5 (magic sets), 13 (tabling), 11 (the code) |
| know what a rule set *means* | 4 (stable models), 15 (open vs closed worlds) |
| get at the theory | 6 (semirings), 9 (Horn clauses), 14 (containment) |
| see where it meets machine learning | 6, 7 (probabilistic) |
| keep answers fresh as data changes | 8 (incremental) |
| reason about definitions, not data | 10 (subsumption) |

**The full list, in file order:**

0. [What is Datalog, and why should you care?](00-what-is-datalog.md)
1. [Facts, rules, and queries](01-first-steps.md)
2. [Recursion and semi-naive evaluation](02-recursion.md)
3. [Negation and stratification](03-negation.md)
4. [Beyond stratification: stable models](04-beyond-stratification.md)
5. [Magic sets: asking questions efficiently](05-magic-sets.md)
6. [Semirings: provenance and recursive aggregation](06-semirings.md)
7. [Probabilistic Datalog, honestly](07-probabilistic.md)
8. [Incremental maintenance](08-incremental.md)
9. [Horn clauses: the boundary Datalog lives on](09-horn-clauses.md)
10. [KL-ONE and subsumption](10-kl-one-subsumption.md)
11. [Under the hood: how this engine is built](11-under-the-hood.md)
12. [Aggregation: counting without contradiction](12-aggregation.md)
13. [Tabling: top-down without the cliff](13-tabling.md)
14. [Containment: the same search, one level up](14-containment.md)
15. [Closed and open worlds](15-closed-and-open-worlds.md)
16. [Writing rules that survive review](16-writing-rules.md)

Three groupings worth knowing about, because each is a single idea told
across several lessons: **3, 4 and 12** share one thesis (finish a
relation before you negate or summarise it); **9 and 13** are one
argument about top-down evaluation; **10 and 15** are a technique
followed by the lesson that examines what it assumed.

Hit a word you don't know? [glossary.md](glossary.md) defines every
technical term the course uses, with the lesson that introduces it.


The lessons build up the whole repository feature by feature:

0. [What is Datalog, and why should you care?](00-what-is-datalog.md) —
   start here if Datalog is new to you: what it is, its history, and why
   it matters in the era of large language models (LLMs)
1. [Facts, rules, and queries](01-first-steps.md)
2. [Recursion and semi-naive evaluation](02-recursion.md)
3. [Negation and stratification](03-negation.md)
4. [Magic sets: asking questions efficiently](05-magic-sets.md)
5. [Beyond stratification: stable models and the café paradox](04-beyond-stratification.md)
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
16. [Writing rules that survive review](16-writing-rules.md)
