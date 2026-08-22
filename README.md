# datalog

Classical Datalog in one file of standard-library Python: parser, safety
checks, **semi-naive evaluation**, **stratified negation**, **magic
sets**, **stable models**, and the **well-founded semantics** — the core
techniques of the deductive-database literature, small enough to read in
an afternoon, with a test suite that doubles as a tour of the classic
example programs.

**What this is:** a teaching and reference implementation. The code
favors readability over speed, the algorithms are the textbook ones, and
the error messages try to teach (a stratification failure reports the
offending cycle through negation).

**What this is not:** an engine to build a product on. Joins are
nested-loop, stable-model search is exhaustive, evaluation is batch. For
real workloads see Soufflé (static analysis), clingo (answer set
programming), RDFox (knowledge graphs), or Feldera (incremental).

## Quick start

```sh
python3 tests.py                                       # 32 tests
python3 datalog.py programs/reachability.dl            # evaluate a program
python3 datalog.py --trace programs/reachability.dl    # + strata, per-round deltas
python3 datalog.py -q 'eats_in_cafe(X)' programs/cafe_foodary.dl
python3 datalog.py --magic -q 'path(n5, X)' programs/reachability.dl  # goal-directed
python3 datalog.py --models programs/cafe_paradox.dl   # stable + well-founded models
```

No dependencies; Python 3.9+.

## Learning Datalog

`docs/` is a short course, each lesson runnable against this engine:

1. [Getting started](docs/getting-started.md) — install, CLI, syntax
2. [Facts, rules, and queries](docs/01-first-steps.md)
3. [Recursion and semi-naive evaluation](docs/02-recursion.md)
4. [Negation and stratification](docs/03-negation.md)
5. [Magic sets: asking questions efficiently](docs/04-magic-sets.md)
6. [Beyond stratification: stable models and the café paradox](docs/05-beyond-stratification.md)

The classics are all in `tests.py`: ancestor, same-generation,
transitive closure (linear and non-linear), mutual recursion, Tweety
default reasoning, the win/move game, the barber paradox, and a miniature
Andersen-style pointer analysis.

## Features

- **Semi-naive evaluation** — each stratum runs to fixpoint, but after
  the first round rules are re-joined only against the previous round's
  *new* facts (the delta), substituted into each recursive body position
  in turn. `--trace` shows the deltas shrinking round by round.
- **Stratified negation** — `not p(...)` is allowed when the program can
  be partitioned into strata so no predicate depends on its own negation.
  Programs with negation inside a recursive cycle are rejected with the
  offending cycle spelled out.
- **Magic sets** (`--magic`, with `-q`) — answers a query by rewriting
  the program (adornments + magic predicates, left-to-right sideways
  information passing) so bottom-up evaluation derives only facts
  relevant to the query's bound arguments. Negated subgoals are not
  specialised — their predicates are computed in full, which keeps the
  rewriting stratified whenever the original program is.
- **Semantic analysis** (`--models`) — for small programs, grounds the
  program and reports all stable models (exhaustive Gelfond–Lifschitz
  check) plus the well-founded three-valued model (Van Gelder's
  alternating fixpoint). Stratifiability is only a syntactic condition;
  this is where the semantic verdict lives.
- Safety checks (range restriction for head and negated variables, ground
  facts, consistent arities) and a tiny Prolog-style syntax:
  `head(X) :- body(X, Y), not other(Y).`

## Magic sets in one look

For `path(n5, X)` on `programs/reachability.dl` the rewriting is:

```prolog
path#bf(X, Y)     :- magic#path#bf(X), edge(X, Y).
magic#path#bf(Y)  :- magic#path#bf(X), edge(X, Y).
path#bf(X, Z)     :- magic#path#bf(X), edge(X, Y), path#bf(Y, Z).
magic#path#bf(n5).
```

`magic#path#bf` collects exactly the start points the query demands, and
every `path` rule is guarded by it, so evaluation never explores the rest
of the graph:

```
[magic] 10 IDB facts derived vs 35 under full evaluation
```

## The café paradox

The repository's flagship example is the **café paradox** — the barber
paradox in catering form. A town's
policy: anyone who does **not** live in a household that cooks its own
meals may eat free in the café. The café is operated by one of the
households, and Bob — a member of that household — is assigned to cook
the café's meals. Where will Bob take his meals?

Three encodings, three verdicts:

- **`programs/cafe_paradox.dl`** reads "a household cooks its own meals"
  as being about the meals its members actually eat. That makes
  `household_cooks` depend on `eats_in_cafe`, which depends on
  `not household_cooks` — the stratified engine rejects the cycle, and
  `--models` shows the rejection is semantically earned: **no stable
  model exists** (the ground core is the `p :- not p` shape — the barber
  paradox in catering form), while the well-founded model settles
  everyone else's meals and leaves *exactly Bob's three atoms undefined*.
  Note the distinction being made: unstratifiable alone doesn't mean
  paradoxical — `win(X) :- move(X, Y), not win(Y)` is unstratifiable yet
  has perfectly good stable models. "No stable model" is the real thing.
- **`programs/cafe_constraint.dl`** reads the argument directly:
  Bob cooks the café's meals, the café is his household, therefore his
  household cooks. The program stratifies, and the paradox surfaces in
  the *data*, as an integrity check naming him and only him:
  `violation(bob).` — the rule itself is ok; the problem arises from the
  situation in which it is applied.
- **`programs/cafe_foodary.dl`** is the resolution: the café's food is
  delivered from another town, nobody local cooks it, the cycle
  disappears, and `eats_in_cafe(bob)` holds.

The full walk-through is
[lesson 5](docs/05-beyond-stratification.md).

## Layout

```
datalog.py     the whole engine (~900 lines): parser, stratifier,
               semi-naive evaluator, magic sets, stable/well-founded models
programs/      café paradox (three encodings) + reachability demo
docs/          getting started + five lessons
tests.py       32 tests; the classic examples live here
```

## License

MIT.
