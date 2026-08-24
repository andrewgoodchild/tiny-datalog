# tiny-datalog

**A logic engine small enough to read in an afternoon, and a course
that builds it up from nothing.**

## What is Datalog?

A query language where you write down facts and rules, and the engine
works out everything that follows.

```prolog
depends(billing, auth).          % facts: things you know
depends(auth, crypto).

uses(X, Y) :- depends(X, Y).                  % a rule: "uses if depends"
uses(X, Z) :- depends(X, Y), uses(Y, Z).      % ...transitively, at any depth
```

`:-` means "if", the comma means "and", capitals are variables. Ask it
what `billing` uses and it answers `auth` and `crypto` — the second
never stated, only implied.

Three properties define it:

- **Declarative.** You say what follows from what. You never say how to
  compute it, in what order, or when to stop.
- **Recursive.** Rules may refer to themselves, so "at any depth"
  questions — reachability, inheritance, containment, dependency — are
  native rather than bolted on.
- **Terminating.** Every Datalog program finishes. Always. That is a
  theorem, not a convention, and it is bought by one deliberate
  restriction ([lesson 9](lessons/09-horn-clauses.md) shows exactly
  which).

It is roughly SQL's SELECT–JOIN plus real recursion and minus the
ceremony, and it is what CodeQL, Datomic, RDFox and Soufflé are
underneath.

## Why Datalog matters in a post-LLM world

Not for the reason science fiction taught us. The trope — feed the
machine a paradox and watch it seize — assumes the machine is a
deductive system, where a contradiction propagates until something
breaks. A language model has no propagation. A contradiction is just
more text, and it glides straight past. You cannot crash it with a
paradox because there is no inference engine in there to crash.

Nor because models are bad at logic. They are conspicuously good at it,
and for an unglamorous reason: logic puzzles are cheap to check, which
makes them excellent reinforcement-learning targets, so the labs have
trained on them heavily. Hand a frontier model a classic paradox and it
will handle it — I tested exactly that on this repository's own example
and it got everything right. Ask one to compute graph reachability *by
writing code* and it scores in the high nineties.

The reason is verification, which is what formal methods have always
been for.

Start from the hardest version of the objection: a model can just write
Python. Forty lines with a breadth-first search gets the same answer as
the example below. If that is the whole task, write the Python.

What you cannot do is ask anything about the Python afterwards.
**Datalog is a deliberately restricted language, and the restriction
buys you a set of questions that are decidable about the rules
themselves:**

| Question about the generated rules | Datalog | Python |
|---|---|---|
| Does it terminate? | yes, by construction | undecidable |
| Are the rules circular? | decidable — names the cycle | — |
| Is there exactly one consistent answer? | decidable | not even well-formed |
| Is this rule redundant given that one? | decidable | undecidable |
| Are these two rule sets equivalent? | decidable (conjunctive) | undecidable |

A model writing Python hands you an answer you must trust. A model
writing Datalog hands you an answer *plus* machine-checkable claims
about the logic that produced it. That is the whole of the difference,
and it exists because the language gave things up.

Three consequences worth naming:

- **The artifact is reviewable by someone who is not a programmer.**
  `eligible(P) :- member(P, H), qualifying_household(H), not employed(P).`
  is nearly the policy sentence. The imperative equivalent is loops and
  mutable state, which a caseworker or an auditor cannot check. When
  machine-written rules govern people, who can read them matters more
  than who can run them.
- **Termination is a safety property.** If you are going to execute
  rules a model wrote, "this halts whatever it generated" is worth a
  great deal, and nothing gives you that for generated code.
- **Provenance and incremental maintenance come from the semantics**
  rather than from more generated code you would also have to verify.

And the boundary, stated plainly, because it is narrower than this
field usually claims for itself. Datalog earns its place when **the
rules outlive the query** — when they are policy rather than a script,
when someone must review them, when an auditor will ask why, when the
data keeps changing, and when *"are these rules even coherent"* is a
question you need answered before trusting any answer they produce.
For a one-off question, or anything arithmetic-heavy, or where nobody
will ask why later, a model and forty lines of Python is the better
tool. That is most problems.

The evidence supports a division of labour rather than a winner:
reasoning in natural-language tokens degrades steeply with problem size,
while the same models writing code that runs against data on disk
barely degrade at all ([numbers below](#should-you-just-ask-a-model-instead)).
**The model's job is to write the rules; the engine's job is to run
them and to check them.**

That makes this repository's features look different than they did
before. Each is a check you would want on machine-written rules:

| The rules might be... | Caught by |
|---|---|
| circular — a condition depending on its own outcome | stratification, which names the cycle |
| self-contradictory | `--models` → *no stable model* |
| silently ambiguous | `--models` → *several stable models* |
| redundant — one rule subsuming another | `containment.py` |
| unsound — an unbound variable | safety validation |
| correct, but needing sign-off | `--explain` → the derivation, not an argument |

The limit is worth stating too: an engine checks *coherence*, not
intent. A rule set can pass every check above and still be the wrong
policy. What formal methods buy is not correctness — it is making the
remaining judgement cheap enough for a human to actually make.

## A worked example

You deploy 12 services. They sit on 160 packages joined by 292
dependency edges — each one individually boring, all of them together
past what anyone holds in their head. A CVE lands on one package. Which
services are exposed?

The 292 edges you wrote down imply **8,457** reachability facts. The
answer is in those, not in the edges, and being 95% right means
shipping a service you believed was clean.

```prolog
% programs/00-supply-chain.dl
uses(X, Y) :- depends(X, Y).
uses(X, Z) :- depends(X, Y), uses(Y, Z).      % ... at any depth

exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).
```

```
$ python3 datalog.py -q 'exposed(S, C)' programs/00-supply-chain.dl
?- exposed(S, C)
   exposed(pkg0, cve_2026_0001).
   exposed(pkg4, cve_2026_0001).
   exposed(pkg5, cve_2026_0001).
   exposed(pkg8, cve_2026_0001).
   (4 answers)
```

Four of twelve — and nothing in the input told you which four.

## Then the questions you actually have next

**"Why pkg4? I need to tell the team what to bump."**

```
$ python3 datalog.py --explain 'exposed(pkg4, cve_2026_0001)' programs/00-supply-chain.dl
?- explain exposed(pkg4, cve_2026_0001)
   exposed(pkg4, cve_2026_0001)   [via exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).]
     service(pkg4)   (base fact)
     uses(pkg4, pkg21)   [via uses(X, Z) :- depends(X, Y), uses(Y, Z).]
       depends(pkg4, pkg13)   (base fact)
       uses(pkg13, pkg21)   [via uses(X, Y) :- depends(X, Y).]
         depends(pkg13, pkg21)   (base fact)
     vulnerable(pkg21, cve_2026_0001)   (base fact)
```

pkg4 → pkg13 → pkg21. Not an explanation *about* the answer — the
derivation the answer came out of, which is what you paste into the
ticket.

**"Another CVE just dropped. Do I rerun everything?"**

No. The engine keeps the 8,457 facts and repairs them:

```python
>>> inc.insert("vulnerable(pkg40, cve_2026_0002).")
{'inserted': 1, 'derived': 12}        # 0.03s, against 0.81s to rebuild
```

**"Is my policy even coherent?"** A different question again, and the
engine answers it — that is
[lesson 5](lessons/05-beyond-stratification.md), worked through on a
benefits policy in `programs/00-eligibility.dl`.

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
