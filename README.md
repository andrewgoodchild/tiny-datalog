# tiny-datalog

**A logic engine small enough to read in an afternoon, and a course
that builds it up from nothing.**

Ask a language model whether Bob qualifies for a benefit and it will
probably be right, and it will explain itself convincingly. But that
explanation is a *separate artifact* from the answer — written by the
same process that sometimes invents citations — so you can't tell a
real derivation from a plausible one without checking it yourself.

Worse, there are questions about a set of rules that no amount of
reading them answers. Is this policy self-contradictory? Does it have
more than one lawful outcome? Which fact is actually doing the work?

A logic engine answers those — not by being cleverer, but by *deriving*
instead of describing. The explanation is the computation that produced
the answer, so it cannot disagree with it, it costs nothing to ask for,
and it comes out identical every time.

Here is what that looks like, on an example small enough to check by
hand.

## A worked example

A council runs a meal-assistance scheme. You can claim if you live in a
household where someone draws a pension — and caring for a pensioner
counts too, even one who lives elsewhere — **unless** you are employed.

Four people in two households: Bob and Cyril share oak_house, Dana and
Edith share elm_house. Cyril draws a pension. Dana has a job. Edith is
Cyril's carer, across the two houses.

Written out, that is seven facts and three rules:

```prolog
% programs/00-eligibility.dl
member(bob,   oak_house).     member(cyril, oak_house).
member(dana,  elm_house).     member(edith, elm_house).

receives_pension(cyril).
employed(dana).
carer(edith, cyril).          % edith cares for cyril, who lives elsewhere

qualifying_household(H) :- member(P, H), receives_pension(P).
qualifying_household(H) :- member(P, H), carer(P, Q), receives_pension(Q).
eligible(P) :- member(P, H), qualifying_household(H), not employed(P).
```

If you have never seen Datalog: `:-` means "if", the comma means "and",
and capital letters are variables standing for "anyone" or "any
household". So the last rule reads *P is eligible if P is a member of
household H, and H qualifies, and P is not employed.* That is most of
the language already.

```
$ python3 datalog.py -q 'eligible(X)' programs/00-eligibility.dl
?- eligible(X)
   eligible(bob).
   eligible(cyril).
   eligible(edith).
   (3 answers)
```

Bob and Cyril through Cyril's pension; Edith because she cares for him.
Dana is out — her household qualifies through Edith, but Dana has a
job.

You could have worked that out yourself, and so could a language model.
Here is what neither of you can do by reading it.

## The policy is ambiguous, and here are both lawful readings

Add the rule every real scheme has — only one member of a household may
claim:

```prolog
% programs/00-eligibility-choice.dl
other_claimant(P) :- member(P, H), member(Q, H), eligible(Q), distinct(P, Q).
eligible(P) :- member(P, H), qualifying_household(H),
               not employed(P), not other_claimant(P).
```

Now ask the engine not "who is eligible?" but "does this policy even
have an answer?" A **stable model** is a complete, self-consistent way
the world could be given these rules — every conclusion supported, no
conclusion contradicted. A policy you can actually operate has exactly
one.

```
$ python3 datalog.py --models programs/00-eligibility-choice.dl
Stable models: 2
  model 1: eligible(bob).  eligible(edith).  other_claimant(cyril).  ...
  model 2: eligible(cyril).  eligible(edith).  other_claimant(bob).  ...
Well-founded model (three-valued):
  true:      eligible(edith).  ...
  undefined: eligible(bob).  eligible(cyril).  ...
```

This one has **two**. The rule never says *which* member claims, so for
oak_house either answer is defensible and the engine spells out both.
The second block is the *well-founded model*, which reports the same
finding a different way: it marks what is settled regardless of how you
resolve the fork. `eligible(edith)` is **true** in it, because
elm_house was never in doubt — only Bob and Cyril are undefined. The
ambiguity is localised to the household that actually has one.

An engine that quietly picked Bob would be worse than useless. This one
says: your policy has a fork, here is exactly where, and you owe it a
tie-break rule — oldest? lowest income? first to apply? That is a
question about the policy rather than about a case, and no amount of
reading seven facts answers it.

**One caveat that belongs here, not in a footnote.** `not employed(P)`
does not mean the person is unemployed. It means the database never
said they were. That is the closed-world assumption, and in a benefits
system it is the difference between "we checked" and "we have no
record" — missing employment data yields a confident `eligible` with an
immaculate proof tree. [Lesson 15](lessons/15-closed-and-open-worlds.md)
is about when that assumption is safe and what the alternative costs.

Two more things the same command finds. Add anti-double-dipping instead
— a household stops qualifying once a member claims — and the policy
self-destructs: **no stable model at all**, because eligibility now
depends on its own outcome (`00-eligibility-paradox.dl`,
[lesson 5](lessons/05-beyond-stratification.md)). And
`--explain 'eligible(bob)'` prints the proof tree any answer came out
of, negative premises included
([lesson 1](lessons/01-first-steps.md)).

| `--models` says | your policy is | what to do |
|---|---|---|
| exactly one stable model | determinate | nothing — this is the goal |
| no stable model | self-contradictory | a condition reads its own outcome; break the loop |
| several stable models | underspecified | consistent, but you owe it a tie-break |

Fixing the middle row is a policy decision, not a syntax trick: the
double-dipping check has to read a **register** maintained elsewhere
rather than this program's own output
(`programs/00-eligibility-stable.dl`). The rule of thumb falls out of
it — **negating a base fact is free; negating a derived predicate is
what forces an order.**

All of these verdicts are *derived* rather than described, which is
what makes them checkable, cheap, and identical on every run. LLMs
generate, logic engines guarantee; the obvious pairing is to let a
model turn a policy document into rules and let the engine decide what
follows from them.

## What's in here

The evaluator that answers all of the above is about 800 lines of
dependency-free Python — genuinely an afternoon's read — surrounded by
eight modules that each add one classical technique, and a 16-lesson
course that builds the whole thing up from facts and rules.

If Datalog is new to you, read
[lesson 0](lessons/00-what-is-datalog.md) first: what it is, where it
came from, and why sound inference is worth more rather than less in
the age of language models. If a term here is unfamiliar,
[the glossary](lessons/glossary.md) defines every one the course uses.

## What you can ask it

Clone it and every row below runs — no dependencies, no install step,
Python 3.9+. This table is the quick start and the table of contents at
once: a question, the command that answers it, and the lesson that
builds it.

```sh
git clone https://github.com/<you>/tiny-datalog && cd tiny-datalog
python3 tests.py        # 119 tests, ~0.7s
```

| Question | Command | Lesson |
|---|---|---|
| What follows from these facts and rules? | `datalog.py programs/01-family.dl` | 1 |
| What's reachable, at any depth? | `datalog.py --trace programs/02-reachability.dl` | 2 |
| What holds *unless* something else does? | `datalog.py programs/03-tweety.dl` | 3 |
| Answer just this query — don't compute everything | `datalog.py --magic -q 'path(n5, X)' programs/02-reachability.dl` | 4 |
| Is this rule set self-contradictory? | `datalog.py --models programs/00-eligibility-paradox.dl` | 5 |
| Why did you conclude that? | `datalog.py --explain 'eligible(bob)' programs/00-eligibility.dl` | 1, 11 |
| Which facts does the conclusion rest on? | `semiring.py -s why programs/06-routes.dl` | 6 |
| What's the cheapest route? How many ways? | `semiring.py -s minplus programs/06-routes.dl` | 6 |
| How likely is it? | `semiring.py -s viterbi programs/07-prob-reach.dl` | 7 |
| The data changed — what changed in the answers? | `incremental.py programs/08-dred-graph.dl -u 'edge(n3, n4)~.'` | 8 |
| How many, how much, largest? | `datalog.py programs/12-spending.dl` | 12 |
| Answer a goal top-down, even left-recursive | `tabling.py programs/13-left-recursive.dl -q 'ancestor(abe, X)'` | 13 |
| What if I allow function symbols — and lose termination? | `prolog.py programs/09-peano.pl -q 'add(X, Y, s(s(zero)))'` | 9 |
| What do these definitions entail about each other? | `subsumption.py programs/10-family-ontology.dl` | 10 |
| Are these two queries the same query? | `containment.py programs/14-minimise.dl` | 14 |

Provenance, in full:

```
$ python3 semiring.py --semiring why -q 'path(a, d)' programs/06-routes.dl
path(a, d) = {edge(a, b), edge(b, c), edge(c, d)} | {edge(a, b), edge(b, d)} | {edge(a, c), edge(c, d)}
```

Three independent derivations, each a minimal set of base facts. Remove
one fact from a witness and that witness fails; remove all three and the
conclusion goes away. That is an audit trail computed rather than
narrated.

## Claims you can check

Every performance claim in the lessons is reproducible from the shipped
generator, including the one that goes the wrong way.

```sh
python3 benchmarks/generate.py chain 150 > chain150.dl
```

| Claim | How to check | Measured here |
|---|---|---|
| Semi-naive beats naive... | `--naive` vs default, chain-50 | 0.7s → 0.07s (**10×**) |
| ...and the gap grows with depth | `--naive` vs default, chain-100 | 10.8s → 0.23s (**47×**) |
| Magic sets makes a *selective* query goal-directed | `--magic -q 'path(n140, X)'`, chain-150 | **66 facts vs 11,175; 0.05s vs 0.62s** |
| Magic sets is not a free lunch | `--magic -q 'path(n1, X)'`, chain-150 | **11,325 facts vs 11,175; 2.19s vs 0.62s** |

The last two rows are the same rewriting on the same program, and they
are the honest pair. Magic sets pays off in proportion to how much the
query's bindings actually prune: ask from the far end of a chain and
demand stays local — 170× fewer facts and 12× faster. Ask from the near
end and demand propagates the chain's whole length, so the rewritten
program derives *more* facts than the original and pays a guard literal
on every join. Nested-loop joins amplify that overhead — each magic guard is a scan
rather than a lookup, which an index would fix — but the governing
variable is demand, not indexing. [Lesson 4](lessons/04-magic-sets.md) works through why.

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
the current research threads. The Lesson column above is the index;
[lessons/getting-started.md](lessons/getting-started.md) has the titles
and the reading order, and
[lessons/glossary.md](lessons/glossary.md) defines every technical term
the course uses.

Every lesson ends with exercises, and every exercise has a worked answer
in `exercises/` — runnable where the answer is a program, and executed
by the test suite so the answers cannot rot. `cases/` lets anyone add a
regression test without writing Python.

## Where these techniques ship

Static analysis at scale (CodeQL, Soufflé) is Datalog. Knowledge graphs
(RDFox) are Datalog. Incremental view maintenance (Feldera) is the 1993
DRed paper with thirty years of engineering on top.
[Lesson 0](lessons/00-what-is-datalog.md) maps every technique in the
course to where it ships.

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
lessons/        getting started, glossary, and lessons 0–15
exercises/      worked answers, verified by the test suite
cases/          golden test cases — add one without writing Python
benchmarks/     scaled input generators (chain/tree/clique/grid)
tests.py        119 tests: every shipped program and exercise answer is
                executed, a conformance suite runs every query through
                every applicable strategy, and a seeded fuzzer checks
                the same property on random programs
```

The code is part of the course: comments explain the algorithms as they
happen, and [lesson 11](lessons/11-under-the-hood.md) is the guided
tour.

### How big is it, honestly

Line counts are `wc -l`, so you can check them:

| | lines |
|---|---|
| the evaluator — AST, parser, safety checks, stratification, semi-naive (`datalog.py` 1–801) | 801 |
| its CLI, result printing, and `--explain` (`datalog.py` 802–1200) | 399 |
| eight satellite modules, one classical technique each | 2,092 |
| **whole toolkit, nine files** | **3,292** |

Of those 3,292 lines: 2,043 are code, 787 are commentary, 462 are
blank. `tests.py` adds a further 1,288, which is the ratio the project
is actually built on — roughly one line of test for every 2.7 lines of
toolkit, and every shipped program, exercise answer and README command
is executed by it.

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
