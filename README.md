# tiny-datalog

**A logic engine small enough to read in an afternoon, and a course
that builds it up from nothing.**

## What is Datalog?

A query language with exactly three properties worth memorising:

- **Declarative** — you state what follows from what, never how to
  compute it. No loops, no ordering, no stopping condition.
- **Recursive** — rules may refer to themselves, so "at any depth"
  questions are the native shape rather than something bolted on.
- **Terminating** — every program finishes. Always. A theorem, not a
  convention.

Here is what that buys you.

You deploy 12 services, sitting on 160 packages joined by 292
dependency edges. A CVE lands on one package. Which services are
exposed?

You write down **facts** — things simply true:

```prolog
depends(pkg4, pkg13).             % pkg4 pulls in pkg13
service(pkg4).                    % pkg4 is something we deploy
vulnerable(pkg21, cve_2026_0001). % pkg21 has the CVE
```

...and **rules** for deriving new facts. `:-` means "if", the comma
means "and", capitals are variables:

```prolog
% programs/00-supply-chain.dl
uses(X, Y) :- depends(X, Y).                  % you use what you depend on
uses(X, Z) :- depends(X, Y), uses(Y, Z).      % ...and whatever that uses

exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).
```

The middle rule reads *X uses Z if X depends on Y and Y uses Z* — it
refers to itself, and that is the whole trick. Applied over and over it
walks the graph to any depth, without you saying how deep or when to
stop.

```
$ python3 datalog.py -q 'exposed(S, C)' programs/00-supply-chain.dl
?- exposed(S, C)
   exposed(pkg0, cve_2026_0001).
   exposed(pkg4, cve_2026_0001).
   exposed(pkg5, cve_2026_0001).
   exposed(pkg8, cve_2026_0001).
   (4 answers)
```

Four of twelve, and nothing you can see in the file says which four:
the 292 edges you *stated* imply **8,457** `uses` facts, and the answer
lives in those. Ask why, and you get the derivation the answer came out
of — which is the remediation path, not a description of it:

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

And when tomorrow's CVE arrives, the engine repairs the 8,457 facts
rather than recomputing them — `{'inserted': 1, 'derived': 12}`, 0.03s
against 0.81s to rebuild.

## Why a language from 1977 still matters

Datalog is old. The field was convened by a 1977 workshop, the name
dates to the early 1980s, and the techniques in this repository were
mostly settled by 1991. So why now?

Not because language models are bad at logic. They are *good* at it.
They have been trained on every logic trope in the canon — Russell's
paradox, the barber, the liar — and they spot contradictions in prose
reliably. Hand a frontier model this repository's own paradox example
and it solves it. Give one more data than it can hold, and it will do
the sensible thing: **write a program.**

Which is exactly the point. When the data is big enough, everyone ends
up running code. The question stops being *whether* to write code and
becomes **what you should have the code do** — and there, the choice of
language decides what you are allowed to ask afterwards.

Have the model write forty lines of Python with a breadth-first search,
and you get the same four services. Have it write Datalog, and you also
get this:

| Question about the rules themselves | Datalog | Python |
|---|---|---|
| Does it terminate? | yes, by construction | undecidable |
| Are the rules circular? | decidable — names the cycle | — |
| Is there exactly one consistent answer? | decidable | not even well-formed |
| Is this rule redundant given that one? | decidable | undecidable |
| Are two rule sets equivalent? | decidable (conjunctive) | undecidable |

Python hands you an answer you must trust. Datalog hands you an answer
*plus* machine-checkable claims about the logic that produced it — and
it can do that precisely because it gave things up. Being declarative,
recursive and terminating is not a feature list; it is the trade that
makes the rules analysable.

Three consequences:

- **The artifact is reviewable by someone who is not a programmer.**
  `eligible(P) :- member(P, H), qualifying_household(H), not employed(P).`
  is nearly the policy sentence. Loops and mutable state are not.
- **Termination is a safety property** when you are executing rules a
  model wrote.
- **Provenance and incremental maintenance come from the semantics**,
  not from more generated code you would also have to verify.

So each feature here is really a check you would want on machine-written
rules:

| The rules might be... | Caught by |
|---|---|
| circular | stratification, which names the cycle |
| self-contradictory | `--models` → *no stable model* |
| silently ambiguous | `--models` → *several stable models* |
| redundant | `containment.py` |
| unsound | safety validation |
| correct, but needing sign-off | `--explain` |

Two honest limits. An engine checks *coherence*, not intent — a rule
set can pass every check and still be the wrong policy. And this trade
only pays when **the rules outlive the query**: policy rather than
script, reviewed, audited, over changing data. For a one-off question,
or anything arithmetic-heavy, forty lines of Python is the better tool.
That is most problems.

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

Every performance claim here is reproducible from the shipped
generator (`python3 benchmarks/generate.py chain 150 > chain150.dl`),
including the one that goes the wrong way.

| Claim | Measured |
|---|---|
| Semi-naive beats naive, and the gap grows | chain-50: 0.7s → 0.07s (**10×**); chain-100: 10.8s → 0.23s (**47×**) |
| Magic sets makes a *selective* query goal-directed | `path(n140, X)`: **66 facts vs 11,175**, 0.05s vs 0.62s |
| Magic sets is not a free lunch | `path(n1, X)`: **11,325 facts vs 11,175**, 2.19s vs 0.62s |

The last two are the same rewriting on the same program. Magic sets
pays in proportion to how much the query's bindings prune; when demand
is the whole relation the guards are pure overhead.
[Lesson 4](lessons/04-magic-sets.md) works through why.

Correctness is checked by a seeded differential fuzzer that generates
stratified programs and demands semi-naive, naive, magic-sets and
tabled evaluation all agree, and that incremental maintenance matches
recomputation under random updates. 400 programs per run;
`TINY_DATALOG_FUZZ=3000 python3 tests.py DifferentialFuzzTests` soaks.

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

## What this is not, and what is missing on purpose

Not an engine to build a product on. Joins are nested-loop,
stable-model search is exhaustive, evaluation is batch. For real
workloads see Soufflé, clingo, RDFox or Feldera.

Deliberate omissions, because saying why teaches more than lacking them
quietly:

- **Arithmetic and comparisons.** A built-in isn't a relation you can
  enumerate, so it must be *evaluated* the moment its operands bind —
  which entangles correctness with join order and forces terms to
  become trees. The principled route is semantic attachments; building
  one is a good exercise.
- **Indexes and join planning.** Every join is a nested loop so the
  algorithms stay one-screen readable. It is also why the magic-sets
  timing above goes the way it does.
- **⊤, ⊥, role hierarchies** in the classifier — what ships is plain
  EL. SNOMED needs ELH with right identities, which is what ELK and
  Snorocket implement and this does not.
- **A REPL and packaging.** `git clone` and run.

Aggregation used to be on this list;
[lesson 12](lessons/12-aggregation.md) is what promoting an omission
into a feature looks like.

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

`wc -l`, so you can check: the evaluator is **801** lines
(`datalog.py` 1–801), its CLI and `--explain` another 399, and eight
satellite modules 2,092 — **3,292** total, of which 2,043 are code, 787
commentary and 462 blank. `tests.py` adds 1,288 more, roughly one test
line per 2.7 lines of toolkit.

"Tiny" is a claim about the evaluator and about each module singly —
none exceeds 380 lines — not about the repository, which is nine
modules because it teaches nine things. There is no dead code to golf
away (checked); shrinking further means deleting a technique or an
explanation.

## License

MIT.
