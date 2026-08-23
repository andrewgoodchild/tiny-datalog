# datalog

Classical Datalog in readable standard-library Python: parser, safety
checks, **semi-naive evaluation**, **stratified negation**, **magic
sets**, **stable models**, and the **well-founded semantics** — the core
techniques of the deductive-database literature, small enough to read in
an afternoon, with a test suite that doubles as a tour of the classic
example programs.

Around the core engine, four satellite modules reach from the classical
canon to the field's modern research threads: **semiring-valued
evaluation** (shortest paths, derivation counting, why-provenance),
**probabilistic facts** (Viterbi), **incremental maintenance** (DRed),
and a **top-down Horn-clause interpreter** marking the boundary Datalog
lives on.

Never met Datalog? Start with
[lesson 0](lessons/00-what-is-datalog.md): what it is, the field's
history from resolution to CodeQL and DBSP — and why sound, auditable
inference matters *more* in a world of LLMs, not less (short version:
LLMs generate; logic engines guarantee).

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
python3 tests.py                                       # 86 tests
python3 datalog.py programs/01-family.dl                  # evaluate a program
python3 datalog.py --trace programs/02-reachability.dl    # + strata, per-round deltas
python3 datalog.py -q 'eats_in_cafe(X)' programs/05-cafe-foodary.dl
python3 datalog.py --magic -q 'path(n5, X)' programs/02-reachability.dl  # goal-directed
python3 datalog.py --models programs/05-cafe-paradox.dl   # stable + well-founded models
python3 semiring.py --semiring minplus programs/06-routes.dl  # shortest paths
python3 semiring.py --semiring why programs/06-routes.dl      # why-provenance
python3 incremental.py                                     # DRed demo
python3 prolog.py programs/09-peano.pl -q 'add(X, Y, s(s(zero)))'  # Horn clauses
python3 subsumption.py programs/10-family-ontology.dl      # classify an ontology
python3 datalog.py programs/12-spending.dl                 # aggregation
python3 datalog.py --explain 'path(n1, n4)' programs/02-reachability.dl  # why?
python3 tabling.py programs/13-left-recursive.dl -q 'ancestor(abe, X)'   # tabled
```

No dependencies; Python 3.9+.

## Learning Datalog

`lessons/` is a complete course — no prior exposure assumed, every
example a runnable file, following the field's own history from 1977 to
the current research threads:

0. [What is Datalog, and why should you care?](lessons/00-what-is-datalog.md) — orientation, history, and the LLM-era case
1. [Getting started](lessons/getting-started.md) — install, CLI, syntax
2. [Facts, rules, and queries](lessons/01-first-steps.md)
3. [Recursion and semi-naive evaluation](lessons/02-recursion.md)
4. [Negation and stratification](lessons/03-negation.md)
5. [Magic sets: asking questions efficiently](lessons/04-magic-sets.md)
6. [Beyond stratification: stable models and the café paradox](lessons/05-beyond-stratification.md)
7. [Semirings: provenance and recursive aggregation](lessons/06-semirings.md)
8. [Probabilistic Datalog, honestly](lessons/07-probabilistic.md)
9. [Incremental maintenance: don't recompute the world](lessons/08-incremental.md)
10. [Horn clauses: the boundary Datalog lives on](lessons/09-horn-clauses.md)
11. [KL-ONE and subsumption: reasoning about definitions](lessons/10-kl-one-subsumption.md)
12. [Under the hood: how this engine is built](lessons/11-under-the-hood.md) — a guided tour of the implementation itself
13. [Aggregation: counting without contradiction](lessons/12-aggregation.md)
14. [Tabling: top-down without the cliff](lessons/13-tabling.md) — and why magic sets was tabling all along

Lesson 0 closes with a technique-by-technique map of where each
lesson's idea ships commercially. Instructors: `ASSIGNMENT.md`
is a ready-to-assign "build your own Datalog" project graded by
differential testing against this repo, and `cases/` lets anyone add a
test without writing Python.

The classic teaching programs ship as runnable files in `programs/` —
family/ancestor, same-generation, transitive closure, mutual recursion
(even/odd), Tweety default reasoning, the win/move game, the barber
paradox, a miniature Andersen-style pointer analysis, weighted routes,
a flaky probabilistic network, and Peano arithmetic — each verified by
the test suite.

## Features

- **Semi-naive evaluation** — each stratum runs to fixpoint, but after
  the first round rules are re-joined only against the previous round's
  *new* facts (the delta), substituted into each recursive body position
  in turn. `--trace` shows the deltas shrinking round by round, and
  `--naive` switches the discipline off so the comparison is measurable.
- **Aggregation** — `total(P, sum(A)) :- charge(P, C, A).` with
  `sum`/`count`/`min`/`max`; the other head arguments are the implicit
  GROUP BY. Aggregation edges are strict in the stratification graph
  (an aggregate must see its whole group), so aggregation-in-a-cycle is
  rejected with the same cycle diagnosis as negation.
- **Derivation trees** (`--explain 'path(a, d)'`) — ask the engine *why*
  it believes a fact: a well-founded proof tree built from
  derivation-order stamps, down to base facts.
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
  `head(X) :- body(X, Y), not other(Y).`  Facts may carry numeric
  weights: `edge(a, b) @ 3.`
- **Semiring evaluation** (`semiring.py`) — the same program computes
  reachability, shortest paths, derivation counts, minimal why-provenance
  witnesses, or best-derivation probabilities, by swapping the (plus,
  times) algebra. Positive programs, Kleene iteration, divergence
  detected and explained.
- **Incremental maintenance** (`incremental.py`) — insertions resume
  semi-naive from a delta; deletions run DRed (over-delete, then
  re-derive survivors). Update scripts mix both: plain facts insert,
  `fact~.` retracts. Every repair is verified against from-scratch
  recomputation in the tests.
- **Tabled evaluation** (`tabling.py`) — top-down with a table per
  subgoal (iterative QSQR): goal-directed like Prolog, terminates like
  Datalog, and handles the left recursion SLD cannot. Its `-t` flag
  prints the tables so you can check they equal the magic sets.
- **Horn clauses beyond Datalog** (`prolog.py`) — a top-down SLD
  interpreter with function symbols, unification (occurs check included),
  negation as failure, and an honest depth bound. The core engine rejects
  function symbols with an error message that states the boundary.
- **Concept subsumption** (`subsumption.py`) — a KL-ONE-style classifier
  for the EL description logic (the fragment that classifies SNOMED CT),
  implemented as a compiler: the ontology is normalised and emitted as a
  plain Datalog program (`--emit` shows it), so classification runs on
  the same engine as everything else.

## Magic sets in one look

For `path(n5, X)` on `programs/02-reachability.dl` the rewriting is:

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

## Deliberately missing

Some absences are design decisions, and saying why teaches more than
quietly lacking them would:

- **Arithmetic and comparisons** (`X + 1`, `X < Y`). A built-in isn't a
  relation you can enumerate — `less_than` has infinitely many rows — so
  it must be *evaluated* at the exact moment its operands become bound.
  That entangles correctness with join order, which this engine keeps
  deliberately naive, and expressions force terms to become trees (the
  function-symbol boundary again, from the inside). The principled
  extension route is *semantic attachments*: a handler that answers
  ground goals like `lt(3, 7)` on demand, registered alongside the pure
  relations. Building one is a good exercise; see also c-cube/datalog's
  design, which documents each such predicate with its own help string.
- **Indexes and join planning.** Every join is a nested loop on purpose:
  the algorithms stay one-screen readable, and the gap to Soufflé's
  compiled indexed joins is Lesson 11's honest-limits discussion, not an
  accident.
- **A REPL and packaging.** Files and flags keep every example
  reproducible from the shell, and zero packaging means the whole thing
  is `git clone` + `python3`.

Aggregation used to be on this list; Lesson 12 is what it looks like to
promote an omission into a feature without breaking the design.

## The café paradox

The repository's flagship example is the **café paradox** — the barber
paradox in catering form. A town's
policy: anyone who does **not** live in a household that cooks its own
meals may eat free in the café. The café is operated by one of the
households, and Bob — a member of that household — is assigned to cook
the café's meals. Where will Bob take his meals?

Three encodings, three verdicts:

- **`programs/05-cafe-paradox.dl`** reads "a household cooks its own meals"
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
- **`programs/05-cafe-constraint.dl`** reads the argument directly:
  Bob cooks the café's meals, the café is his household, therefore his
  household cooks. The program stratifies, and the paradox surfaces in
  the *data*, as an integrity check naming him and only him:
  `violation(bob).` — the rule itself is ok; the problem arises from the
  situation in which it is applied.
- **`programs/05-cafe-foodary.dl`** is the resolution: the café's food is
  delivered from another town, nobody local cooks it, the cycle
  disappears, and `eats_in_cafe(bob)` holds.

The full walk-through is
[lesson 5](lessons/05-beyond-stratification.md).

## Layout

```
datalog.py      the core: AST, parser, safety checks, stratification,
                the semi-naive evaluator, and the CLI
magic.py        the magic-sets rewriting (a program-to-program pass)
semantics.py    grounding, stable models, the well-founded model
semiring.py     semiring-valued evaluation (costs, counts, provenance,
                probabilities)
incremental.py  insertions + DRed deletions over a live materialisation
prolog.py       top-down SLD resolution with function symbols
tabling.py      tabled top-down evaluation (iterative QSQR)
subsumption.py  KL-ONE-style EL classifier, compiled to Datalog
programs/       the classic teaching programs, numbered by lesson
                (01-family.dl ... 13-left-recursive.dl), plus the café
                paradox
lessons/        getting started + lessons 0–13, following the field's
                history from 1977 to the current research threads
cases/          golden test cases — add one without writing Python
benchmarks/     scaled input generators (chain/tree/clique/grid)
ASSIGNMENT.md   a build-your-own-Datalog course project, graded by
                differential testing against this repo
tests.py        86 tests — every shipped program is exercised, and a
                conformance suite runs every query through every
                applicable evaluation strategy
```

The code itself is part of the course: comments explain the algorithms
as they happen, and [lesson 10](lessons/11-under-the-hood.md) is the
guided tour.

## License

MIT.
