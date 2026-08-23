# tiny-datalog

Ask a language model whether Bob is eligible and it will probably be
right, and it can talk you through why. The gap isn't capability — it's
that the explanation is a *separate artifact* from the answer, produced
by the same process that sometimes invents citations. You can't tell a
real derivation from a plausible one without checking it yourself.

A logic engine has no gap to fall through: the derivation **is** the
computation. Ask why and you get the proof tree the answer came out of,
identically every time, over a database far larger than a context
window, at no extra cost — the engine already did the work. Ask whether
the policy contradicts itself and you get a decision, not an opinion.

That trade is what this repository is about. The evaluator is about 650
lines of dependency-free Python — genuinely an afternoon's read — plus
eight modules that each add one classical technique, and a 15-lesson
course that builds the whole thing up from facts and rules.

**Why does it believe that?** Here is the policy — the shape every
benefits rule, access-control list and compliance check is made of:

```prolog
% programs/00-eligibility.dl
qualifying_household(H) :- member(P, H), receives_pension(P).
qualifying_household(H) :- member(P, H), carer(P, Q), receives_pension(Q).
eligible(P) :- member(P, H), qualifying_household(H), not employed(P).
```

```
$ python3 datalog.py --explain 'eligible(bob)' programs/00-eligibility.dl
?- explain eligible(bob)
   eligible(bob)   [via eligible(P) :- member(P, H), qualifying_household(H), not employed(P).]
     member(bob, oak_house)   (base fact)
     qualifying_household(oak_house)   [via qualifying_household(H) :- member(P, H), receives_pension(P).]
       member(cyril, oak_house)   (base fact)
       receives_pension(cyril)   (base fact)
     not employed(bob)   (absent from its completed stratum)
```

Bob qualifies through his housemate's pension, and the negative
condition that had to hold is stated as explicitly as the positive ones.
Dana, in a household that also qualifies but employed, is simply absent
from `eligible` — the rule discriminates, and the tree shows exactly
which fact does the discriminating.

**Is the policy even coherent?** Push the same shape of rule one step
further — make the benefit's condition depend on who claims it — and:

```
$ python3 datalog.py programs/05-cafe-paradox.dl
REJECTED: program is not stratifiable — negation occurs inside a recursive
cycle: eats_in_cafe --not--> household_cooks --> eats_in_cafe.  No stratum
assignment exists, so the program has no stratified model.
(This is a syntactic verdict.  Run with --models for the semantic one:
stable models and the well-founded model.)
```

Both answers are *derived*, not described — which is what makes them
checkable, cheap, and identical on every run. That is the case for
knowing this material: LLMs generate, logic engines guarantee, and the
interesting systems use each for what it is good at. (The obvious
pairing: let the model turn a policy document into rules, and let the
engine decide what follows from them.)

Never met Datalog? Start with
[lesson 0](lessons/00-what-is-datalog.md) — what it is, the field's
history from resolution to CodeQL and DBSP, and where each technique
ships today.

## What it answers

| Question | Command | In the literature |
|---|---|---|
| Why did you conclude that? | `datalog.py --explain 'f(a)'` | derivation trees, down to base facts |
| Which facts does it rest on? | `semiring.py --semiring why` | minimal why-provenance witnesses |
| Is this rule set consistent? | `datalog.py --models` | stable models + well-founded model |
| Where exactly is the circularity? | any run | stratification error naming the cycle |
| What follows from these definitions? | `subsumption.py` | EL concept classification |

Provenance, in full:

```
$ python3 semiring.py --semiring why -q 'path(a, d)' programs/06-routes.dl
path(a, d) = {edge(a, b), edge(b, c), edge(c, d)} | {edge(a, b), edge(b, d)} | {edge(a, c), edge(c, d)}
```

Three independent derivations, each a minimal set of base facts. Remove
one fact from a witness and that witness fails; remove all three and the
conclusion goes away. That is an audit trail computed rather than
narrated.

## Quick start

```sh
python3 tests.py                                          # 114 tests, ~0.6s
python3 datalog.py -q 'eligible(X)' programs/00-eligibility.dl
python3 datalog.py --explain 'eligible(bob)' programs/00-eligibility.dl
python3 datalog.py programs/01-family.dl                  # evaluate a program
python3 datalog.py --trace programs/02-reachability.dl    # + strata, per-round deltas
python3 datalog.py -q 'eats_in_cafe(X)' programs/05-cafe-foodary.dl
python3 datalog.py --magic -q 'path(n5, X)' programs/02-reachability.dl
python3 datalog.py --models programs/05-cafe-paradox.dl
python3 datalog.py programs/12-spending.dl                     # aggregation
python3 semiring.py --semiring minplus programs/06-routes.dl   # shortest paths
python3 incremental.py                                         # DRed demo
python3 prolog.py programs/09-peano.pl -q 'add(X, Y, s(s(zero)))'
python3 subsumption.py programs/10-family-ontology.dl          # classify an ontology
python3 tabling.py programs/13-left-recursive.dl -q 'ancestor(abe, X)'
python3 containment.py programs/14-minimise.dl                 # minimise queries
```

No dependencies; Python 3.9+. No packaging, no REPL, no install step —
`git clone` and run.

## Claims you can check

Every performance claim in the lessons is reproducible from the shipped
generator, including the one that goes the wrong way.

```sh
python3 benchmarks/generate.py chain 150 > chain150.dl
```

| Claim | How to check | Measured here |
|---|---|---|
| Semi-naive beats naive, and the gap grows with depth | `--naive` vs default, chain-100 | **10.6s → 0.23s (46×)** |
| Magic sets makes a *selective* query goal-directed | `--magic -q 'path(n140, X)'`, chain-150 | **66 facts vs 11,175; 0.05s vs 0.62s** |
| Magic sets is not a free lunch | `--magic -q 'path(n1, X)'`, chain-150 | **11,325 facts vs 11,175; 2.19s vs 0.62s** |

The last two rows are the same rewriting on the same program, and they
are the honest pair. Magic sets pays off in proportion to how much the
query's bindings actually prune: ask from the far end of a chain and
demand stays local — 170× fewer facts and 12× faster. Ask from the near
end and demand propagates the chain's whole length, so the rewritten
program derives *more* facts than the original and pays a guard literal
on every join. Nested-loop joins amplify that overhead (an index would
soften the bad case), but the governing variable is demand, not
indexing. [Lesson 4](lessons/04-magic-sets.md) works through why.

Correctness claims are checked too, by a seeded differential fuzzer
(`DifferentialFuzzTests`) that generates stratified programs and demands
that semi-naive, naive, magic-sets and tabled evaluation agree on every
query, and that incremental maintenance matches from-scratch
recomputation under random insert/delete sequences. 400 programs per
test run; `TINY_DATALOG_FUZZ=3000 python3 tests.py DifferentialFuzzTests`
for a real soak.

## Learning Datalog

`lessons/` is a complete course — no prior exposure assumed, every
example a runnable file, following the field's own history from 1977 to
the current research threads. Numbers below are the lesson numbers the
lessons themselves use:

- [Getting started](lessons/getting-started.md) — CLI and syntax
- [0 · What is Datalog, and why should you care?](lessons/00-what-is-datalog.md) — orientation, history, the LLM-era case
- [1 · Facts, rules, and queries](lessons/01-first-steps.md)
- [2 · Recursion and semi-naive evaluation](lessons/02-recursion.md)
- [3 · Negation and stratification](lessons/03-negation.md)
- [4 · Magic sets: asking questions efficiently](lessons/04-magic-sets.md)
- [5 · Beyond stratification: stable models and the café paradox](lessons/05-beyond-stratification.md)
- [6 · Semirings: provenance and recursive aggregation](lessons/06-semirings.md)
- [7 · Probabilistic Datalog, honestly](lessons/07-probabilistic.md)
- [8 · Incremental maintenance: don't recompute the world](lessons/08-incremental.md)
- [9 · Horn clauses: the boundary Datalog lives on](lessons/09-horn-clauses.md)
- [10 · KL-ONE and subsumption: reasoning about definitions](lessons/10-kl-one-subsumption.md)
- [11 · Under the hood: how this engine is built](lessons/11-under-the-hood.md)
- [12 · Aggregation: counting without contradiction](lessons/12-aggregation.md)
- [13 · Tabling: top-down without the cliff](lessons/13-tabling.md)
- [14 · Containment: the same search, one level up](lessons/14-containment.md)

Every lesson ends with exercises, and every exercise has a worked answer
in `exercises/` — runnable where the answer is a program, and executed
by the test suite so the answers cannot rot. `cases/` lets anyone add a
regression test without writing Python.

## Where these techniques ship

| Technique | Lesson | In production |
|---|---|---|
| Semi-naive evaluation | 2 | every deductive database |
| Stratified negation | 3 | Soufflé, CodeQL, RDFox |
| Magic sets | 4 | Soufflé's transform, LogicBlox demand transformation |
| Stable models | 5 | clingo — configuration, scheduling |
| Provenance semirings | 6 | data lineage, Soufflé's provenance debugger |
| Incremental maintenance | 8 | Differential Dataflow, DBSP, Feldera, Materialize |
| Tabling | 13 | XSB, SWI-Prolog |
| EL classification | 10 | ELK, Snorocket, SNOMED CT tooling |
| Containment & minimisation | 14 | every SQL optimiser's rewrite stage |

Static analysis at scale (CodeQL, Soufflé) is Datalog. Knowledge graphs
(RDFox) are Datalog. Incremental view maintenance (Feldera) is the 1993
DRed paper with thirty years of engineering on top. Lesson 0 has the
lesson-by-lesson map.

## Features

- **Semi-naive evaluation** — each stratum runs to fixpoint; after round
  one, rules re-join only against the previous round's new facts,
  substituted into each recursive body position in turn. `--trace` shows
  the deltas shrinking; `--naive` switches the discipline off so the
  comparison is measurable.
- **Stratified negation** — `not p(...)` is allowed when the program
  partitions into strata so no predicate depends on its own negation.
  Violations are rejected with the offending cycle spelled out.
- **Derivation trees** (`--explain`) — a proof tree built from
  derivation-order stamps, so a fact can never justify itself.
- **Magic sets** (`--magic`) — adornments, magic predicates, and
  left-to-right sideways information passing, so bottom-up evaluation
  derives only what a top-down engine would have visited. Negated
  subgoals are not specialised, which keeps the rewriting stratified
  whenever the original program is.
- **Semantic analysis** (`--models`) — grounds small programs and
  reports every stable model (exhaustive Gelfond–Lifschitz check) plus
  the well-founded three-valued model (Van Gelder's alternating
  fixpoint). Stratifiability is only syntactic; this is where the
  semantic verdict lives.
- **Aggregation** — `total(P, sum(A)) :- charge(P, C, A).` with
  `sum`/`count`/`min`/`max`; other head arguments are the implicit GROUP
  BY, and aggregates range over distinct body *solutions*, as in SQL and
  Soufflé. Aggregation edges are strict in the stratification graph, so
  aggregation-in-a-cycle is rejected with the same cycle diagnosis as
  negation.
- **Semiring evaluation** (`semiring.py`) — one program computes
  reachability, shortest paths, derivation counts, why-provenance
  witnesses, or best-derivation probabilities, by swapping the (plus,
  times) algebra. Divergence is detected and explained.
- **Incremental maintenance** (`incremental.py`) — insertions resume
  semi-naive from a delta; deletions run DRed (over-delete, then
  re-derive survivors). `fact~.` retracts. Every repair is verified
  against from-scratch recomputation, including under fuzzing.
- **Tabled evaluation** (`tabling.py`) — top-down with a table per
  subgoal (iterative QSQR): goal-directed like Prolog, terminating like
  Datalog, and it handles the left recursion SLD cannot. `-t` prints the
  tables so you can check they equal the magic sets.
- **Horn clauses beyond Datalog** (`prolog.py`) — top-down SLD with
  function symbols, unification (occurs check included), negation as
  failure, and an honest depth bound. The core engine rejects function
  symbols with an error that states the boundary.
- **Concept subsumption** (`subsumption.py`) — a KL-ONE-style classifier
  for the EL description logic, implemented as a compiler: the ontology
  is normalised and emitted as plain Datalog (`--emit` shows it), so
  classification runs on the same engine as everything else.

## What this is not

An engine to build a product on. Joins are nested-loop, stable-model
search is exhaustive, evaluation is batch. For real workloads see
Soufflé (static analysis), clingo (answer set programming), RDFox
(knowledge graphs), or Feldera (incremental).

The code favours readability over speed, the algorithms are the textbook
ones, and the error messages try to teach.

## Deliberately missing

Some absences are design decisions, and saying why teaches more than
quietly lacking them would:

- **Arithmetic and comparisons** (`X + 1`, `X < Y`). A built-in isn't a
  relation you can enumerate — `less_than` has infinitely many rows — so
  it must be *evaluated* at the moment its operands become bound. That
  entangles correctness with join order, which this engine keeps
  deliberately naive, and expressions force terms to become trees (the
  function-symbol boundary again, from the inside). The principled route
  is semantic attachments: a handler answering ground goals like
  `lt(3, 7)` on demand. Building one is a good exercise.
- **Indexes and join planning.** Every join is a nested loop on purpose:
  the algorithms stay one-screen readable, and the gap to Soufflé's
  compiled indexed joins is
  [lesson 11](lessons/11-under-the-hood.md)'s honest-limits discussion,
  not an accident.
- **⊤, ⊥, role hierarchies and right identities** in the classifier.
  What ships is plain EL. SNOMED CT needs ELH with right identities —
  the extension ELK and Snorocket implement — so this classifier
  demonstrates the calculus SNOMED-scale reasoners are built on without
  being able to classify SNOMED itself. The completion-rule approach
  generalises; these five rules do not cover it.
- **A REPL and packaging.** Files and flags keep every example
  reproducible from the shell, and zero packaging means the whole thing
  is `git clone` + `python3`.

Aggregation used to be on this list;
[lesson 12](lessons/12-aggregation.md) is what it looks like to promote
an omission into a feature without breaking the design.

## The café paradox

The flagship example is the **café paradox** — the barber paradox in
catering form, and a stand-in for any eligibility rule that quietly
refers to its own outcome. A town's policy: anyone who does *not* live
in a household that cooks its own meals may eat free in the café. The
café is operated by one of the households, and Bob — a member of that
household — is assigned to cook the café's meals. Where does Bob eat?

Three encodings, three verdicts:

- **`programs/05-cafe-paradox.dl`** reads "a household cooks its own
  meals" as being about the meals its members actually eat. The
  stratified engine rejects the cycle, and `--models` shows the
  rejection is semantically earned: **no stable model exists** — the
  ground core is the `p :- not p` shape — while the well-founded model
  settles everyone else and leaves *exactly Bob's three atoms
  undefined*. Note the distinction: unstratifiable alone doesn't mean
  paradoxical. `win(X) :- move(X, Y), not win(Y)` is unstratifiable yet
  has perfectly good stable models. "No stable model" is the real thing.
- **`programs/05-cafe-constraint.dl`** reads the argument directly. The
  program stratifies, and the paradox surfaces in the *data*, as an
  integrity check naming him and only him: `violation(bob).` The rule is
  fine; the situation it was applied to is not.
- **`programs/05-cafe-foodary.dl`** is the resolution: the café's food
  is delivered from another town, the cycle disappears, and
  `eats_in_cafe(bob)` holds.

Full walk-through in
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
containment.py  query containment and minimisation by homomorphism
programs/       the classic teaching programs, numbered by lesson
lessons/        getting started + lessons 0–14
exercises/      worked answers, verified by the test suite
cases/          golden test cases — add one without writing Python
benchmarks/     scaled input generators (chain/tree/clique/grid)
tests.py        114 tests: every shipped program and exercise answer is
                executed, a conformance suite runs every query through
                every applicable strategy, and a seeded fuzzer checks
                the same property on random programs
```

The code is part of the course: comments explain the algorithms as they
happen, and [lesson 11](lessons/11-under-the-hood.md) is the guided
tour.

### How big is it, honestly

| | lines |
|---|---|
| the evaluator (AST, parser, safety, stratification, semi-naive) | **~650** |
| its CLI, printing, and `--explain` | ~330 |
| eight satellite modules, one classical technique each | ~2,100 |
| whole toolkit, nine files | 3,292 — of which 2,043 are code and 787 are commentary |

"Tiny" is a claim about the evaluator, and about each module taken on
its own: none is longer than 380 lines, and every one is meant to be
read start to finish. It is not a claim that the whole repository is
small — it is nine modules because it teaches nine things.

The commentary is not overhead to be trimmed. It is roughly a quarter
of the file volume on purpose: this is a repository where the source is
assigned reading, so the explanation lives next to the code rather than
only in the lessons. There is no dead code to golf away (checked), and
shrinking it further would mean deleting either a technique or an
explanation.

## License

MIT.
