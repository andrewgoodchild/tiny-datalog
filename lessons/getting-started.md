# Getting started

Everything is one file of standard-library Python — there is nothing to
install beyond Python 3.9+.

```sh
git clone https://github.com/andrewgoodchild/tiny-datalog
cd tiny-datalog
python3 tests.py                     # 127 tests, should all pass
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
| `python3 incremental.py prog.dl -u 'f(a)~. f(b).'` | apply retractions/insertions to a live materialisation (`--strategy bf` checks before deleting) |
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


The lessons are numbered in reading order. Lessons 1–5 are the spine
and everything after assumes them: facts and rules, recursion,
negation, what negation *assumes* (closed vs open worlds), and what an
unstratifiable program *means* (stable models). After the spine there
is no single mandatory sequence — the paths below say what to read for
a given purpose.

| If you are here to... | Read |
|---|---|
| write rules for a real policy | 13 (aggregation), 4 (missing data), 6 (for-all), 17 (authoring) |
| understand how evaluation works | 2, 7 (magic sets), 15 (tabling), and the *Under the hood* sections |
| know what a rule set *means* | 5 (stable models), 4 (open vs closed worlds) |
| get at the theory | 8 (semirings), 11 (Horn clauses), 16 (containment), 18 (category theory) |
| see where it meets machine learning | 8, 9 (probabilistic) |
| keep answers fresh as data changes | 10 (incremental) |
| reason about definitions, not data | 12 (subsumption) |

**The full list:**

0. [What is Datalog, and why should you care?](00-what-is-datalog.md)
1. [Facts, rules, and queries](01-first-steps.md)
2. [Recursion and semi-naive evaluation](02-recursion.md)
3. [Negation and stratification](03-negation.md)
4. [Closed and open worlds](04-closed-and-open-worlds.md)
5. [Beyond stratification: stable models](05-beyond-stratification.md)
6. [For all, in a language that only has there-exists](06-for-all.md)
7. [Magic sets: asking questions efficiently](07-magic-sets.md)
8. [Semirings: provenance and recursive aggregation](08-semirings.md)
9. [Probabilistic Datalog, honestly](09-probabilistic.md)
10. [Incremental maintenance](10-incremental.md)
11. [Horn clauses: the boundary Datalog lives on](11-horn-clauses.md)
12. [KL-ONE and subsumption](12-kl-one-subsumption.md)
13. [Aggregation, and the lattices beyond it](13-aggregation.md)
14. [Arithmetic: the price of numbers](14-arithmetic.md)
15. [Tabling: top-down without the cliff](15-tabling.md)
16. [Containment: the same search, one level up](16-containment.md)
17. [Writing rules that survive review](17-writing-rules.md)
18. [The road not taken: category theory](18-category-theory.md)

Three groupings worth knowing about, because each is a single idea told
across several lessons: **3, 5 and 12** share one thesis (finish a
relation before you negate or summarise it); **10 and 13** are one
argument about top-down evaluation; **4 and 12** are one contrast
met twice — 4 shows closed against open worlds from the data side,
and 12 builds the reasoner living on the other side of it.

Hit a word you don't know? [glossary.md](glossary.md) defines every
technical term the course uses, with the lesson that introduces it.
