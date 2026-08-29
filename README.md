# tiny-datalog

[![tests](https://github.com/andrewgoodchild/tiny-datalog/actions/workflows/ci.yml/badge.svg)](https://github.com/andrewgoodchild/tiny-datalog/actions/workflows/ci.yml)

**A logic engine small enough to read in an afternoon, and a course
that builds it up from nothing.**

## What is Datalog?

A query language from the early 1980s, with three properties worth
memorising:

- **Declarative.** You state what follows from what, never how to
  compute it. No loops, no ordering, no stopping condition.
- **Recursive.** Rules may refer to themselves, so "at any depth"
  questions are the native shape rather than something bolted on.
- **Terminating.** Every program finishes. Always. That is a theorem,
  not a convention.

Datalog is useful when a query is recursive and SQL is fighting you,
or when a rule set has grown past the point where anyone can review
it. Here is what that buys you.

You deploy 12 services, sitting on 160 packages joined by 292
dependency edges. A CVE (Common Vulnerabilities and Exposures entry, a
published security flaw) lands on one package. Which services are
exposed?

You write down **facts**, things simply true:

```prolog
depends(pkg4, pkg13).             % pkg4 pulls in pkg13
service(pkg4).                    % pkg4 is something we deploy
vulnerable(pkg21, cve_2026_0001). % pkg21 has the CVE
```

...and **rules** for deriving new facts. `:-` means "if", the comma
means "and", capitals are variables:

```prolog
% programs/supply-chain.dl
uses(X, Y) :- depends(X, Y).                  % you use what you depend on
uses(X, Z) :- depends(X, Y), uses(Y, Z).      % ...and whatever that uses

exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).
```

The middle rule reads *X uses Z if X depends on Y and Y uses Z*. It
refers to itself, and that is the whole trick: applied over and over it
walks the graph to any depth, without you saying how deep or when to
stop.

```
$ python3 datalog.py -q 'exposed(S, C)' programs/supply-chain.dl
?- exposed(S, C)
   exposed(pkg0, cve_2026_0001).
   exposed(pkg4, cve_2026_0001).
   exposed(pkg5, cve_2026_0001).
   exposed(pkg8, cve_2026_0001).
   (4 answers)
```

Four of twelve, and nothing you can see in the file says which four.
The 292 edges you stated imply 8,457 `uses` facts, and the answer lives
in those. Ask why, and you get the derivation the answer came out of,
which is also the remediation path:

```
$ python3 datalog.py --explain 'exposed(pkg4, cve_2026_0001)' programs/supply-chain.dl
?- explain exposed(pkg4, cve_2026_0001)
   exposed(pkg4, cve_2026_0001)   [via exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).]
     service(pkg4)   (base fact)
     uses(pkg4, pkg21)   [via uses(X, Z) :- depends(X, Y), uses(Y, Z).]
       depends(pkg4, pkg13)   (base fact)
       uses(pkg13, pkg21)   [via uses(X, Y) :- depends(X, Y).]
         depends(pkg13, pkg21)   (base fact)
     vulnerable(pkg21, cve_2026_0001)   (base fact)
```

When tomorrow's CVE arrives, the engine repairs those 8,457 facts
instead of recomputing them:

```
$ python3 incremental.py programs/supply-chain.dl -u 'vulnerable(pkg100, cve_2026_0002).'
materialised: 8766 facts
vulnerable(pkg100, cve_2026_0002).
  -> {'inserted': 1, 'derived': 12} in 0.034s
  (a from-scratch rebuild of this program: 0.822s)
```

Nothing to install:

```sh
git clone https://github.com/andrewgoodchild/tiny-datalog && cd tiny-datalog
python3 tests.py        # 127 tests, ~7s
```

## Why the language choice decides what you can ask later

Frontier language models are getting good at reasoning and logic. They
have been trained on every logic trope in the canon, they can usually
spot a contradiction in prose, and when they meet more data than fits
in a context window they do the sensible thing: they write a program to
solve it.

So the question was never whether to run code. It is what the code
should be, and that choice decides which questions you can still ask
afterwards.

Rules that encode policy tend to outlive the query that prompted them.
They get reviewed, audited, inherited by someone who did not write
them, and changed under pressure. Sooner or later somebody asks why a
particular decision came out the way it did, and somebody else asks
whether the rules are even coherent before trusting any answer at all.

(The sign-off case has its own demonstration:
[lesson 17](lessons/17-writing-rules.md) writes a lending policy badly
twice, and `--explain` names which of two rules wrongly let a
suspended staff member borrow — three lines, no debugger.)

Both are questions about the rules, not about a run, and most languages
cannot answer them. Datalog can, because it gave things up:

| Question about the rules themselves | Datalog | A general-purpose program |
|---|---|---|
| Does it terminate? | yes, by construction | undecidable |
| Are the rules circular? | decidable, and it names the cycle | n/a, recursion is ordinary |
| Is there exactly one consistent answer? | decidable | not even well-formed |
| Is one rule redundant given another? | decidable for the non-recursive fragment | undecidable |
| Are two rule sets equivalent? | decidable for the non-recursive fragment | undecidable |

(Containment and equivalence become undecidable once recursion is
involved — Shmueli, 1993, which is why `containment.py` handles
conjunctive queries and refuses the rest.
[Lesson 16](lessons/16-containment.md) covers the boundary.)

Being declarative, recursive and terminating is not a feature list. It
is the trade that makes rules analysable, and three things follow from
it:

- **The artifact is reviewable by someone who is not a programmer.**
  `eligible(P) :- member(P, H), qualifying_household(H), not employed(P).`
  is nearly the policy sentence. Loops and mutable state are not.
- **Termination is a safety property**, not a nicety, when the rules
  are going to be executed by something you do not supervise.
- **Provenance and incremental maintenance come from the semantics**
  rather than from extra code that would itself need verifying.

Every feature in this repository is a check of that kind: stratification
catches circularity, `--models` catches contradiction and ambiguity,
`containment.py` catches redundancy, and `--explain` produces the
derivation somebody has to sign off on.

Two limits. An engine checks coherence, not intent: a rule set can pass
every check above and still be the wrong policy. And the trade only
pays when the rules genuinely outlive the query. For a one-off
question, or anything arithmetic-heavy, forty lines of ordinary code is
the better tool, and that covers most problems.

## What else you can ask it

The worked example above is one row of a table. Lesson 0 ends with the
full version — 20 questions, each with the command that answers it and
the lesson that builds the machinery:
[lesson 0](lessons/00-what-is-datalog.md).

## Claims you can check

Beyond the benchmarks: **every shell command quoted in every lesson is
executed in CI and its quoted output diffed against reality** — the
course cannot silently rot, which is a rarer property than anything
else on this page. Every performance claim below is reproducible from
the shipped generator, including the one that goes the wrong way. Timings are on an
Apple M1 Pro, CPython 3.10, single core:

```sh
python3 benchmarks/generate.py chain 50  > chain50.dl
python3 benchmarks/generate.py chain 100 > chain100.dl
python3 benchmarks/generate.py chain 150 > chain150.dl
```

| Claim | Measured |
|---|---|
| Semi-naive beats naive, and the gap grows | chain-50: 0.7s → 0.07s (**10×**); chain-100: 10.7s → 0.22s (**48×**) |
| Magic sets makes a *selective* query goal-directed | `path(n140, X)`: **66 facts vs 11,175**, 0.05s vs 0.62s |
| Magic sets is not a free lunch | `path(n1, X)`: **11,325 facts vs 11,175**, 2.19s vs 0.62s |

The last two are the same rewriting on the same program. Magic sets
pays in proportion to how much the query's bindings prune; when demand
is the whole relation the guards are pure overhead.
[Lesson 7](lessons/07-magic-sets.md) works through why.

Correctness is checked by a seeded differential fuzzer that generates
stratified programs and demands semi-naive, naive, magic-sets and
tabled evaluation all agree, and that incremental maintenance matches
recomputation under random updates. 400 programs per run;
`TINY_DATALOG_FUZZ=3000 python3 tests.py DifferentialFuzzTests` soaks.

## Learning Datalog

`lessons/` is a complete course, no prior exposure assumed, every
example a runnable file, following the field's own history from 1977 to
the current research threads. The field's own recent lecture notes
observe that the literature advises people building Datalog engines
better than people trying to *use* one; this course does both halves
on purpose — sixteen lessons where the engine is the explanation, then
a lesson on authoring rules that survive review. And it is built to be
inherited: `git clone`, no dependencies, no hosted anything, and every
quoted transcript re-verified by CI — the exercises cannot rot. (For where each
technique ships — CodeQL, RDFox, Feldera, SNOMED and the rest —
[lesson 0](lessons/00-what-is-datalog.md) ends with the deployments.)
[lessons/getting-started.md](lessons/getting-started.md) has the titles
and the reading order, and
[lessons/glossary.md](lessons/glossary.md) defines every technical term
the course uses.

Three of them teach things that are hard to find taught well anywhere
else, and they are the reason the course exists rather than just the
engine:

- **[Lesson 8](lessons/08-semirings.md)** proves that why-provenance
  cannot be specialised into derivation counts, with a program that
  prints the disproof: two facts with identical provenance and different
  counts. That settles "materialise provenance once, specialise later,"
  which is a real design-review question with a real answer.
- **[Lesson 16](lessons/16-containment.md)** shows that the containment
  test you need for query minimisation is the search already sitting in
  `datalog.py`: `_match` maps a rule body into a database,
  `find_homomorphism` maps a rule body into another rule body. Same
  backtracking, one level up.
- **[Lesson 4](lessons/04-closed-and-open-worlds.md)** contrasts the
  two reasoners in this repository, which disagree about what absence
  means, and leaves you with a habit: when you see `not`, ask whose
  authority says this is absent.

Every lesson ends with exercises, and every exercise has a worked answer
in `exercises/` — runnable where the answer is a program, and executed
by the test suite so the answers cannot rot. `cases/` lets anyone add a
regression test without writing Python.

## What this is not, and what is missing on purpose

Not an engine to build a product on. Joins are nested-loop,
stable-model search is exhaustive, evaluation is batch. For real
workloads see Soufflé, clingo, RDFox or Feldera.

Deliberate omissions, because saying why teaches more than lacking them
quietly:

- **Arithmetic and comparisons.** A built-in isn't a relation you can
  enumerate, so it must be *evaluated* the moment its operands bind —
  which entangles correctness with join order and forces terms to
  become trees. [Lesson 14](lessons/14-arithmetic.md) is the whole
  story, including what to do instead.
- **Indexes and join planning.** Every join is a nested loop so the
  algorithms stay one-screen readable. It is also why the magic-sets
  timing above goes the way it does.
- **⊤ and role hierarchies** in the classifier — what ships is EL⊥
  (disjointness and unsatisfiability detection included). SNOMED needs
  ELH (EL plus role hierarchies) with right identities, which is what
  the ELK and Snorocket reasoners implement and this does not.
- **A REPL (interactive prompt) and packaging.** `git clone` and run.

Aggregation used to be on this list;
[lesson 13](lessons/13-aggregation.md) is what promoting an omission
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
programs/       teaching programs, numbered by the lesson that uses
                them (00-* are the README's examples)
lessons/        getting started, glossary, and lessons 0–18
exercises/      worked answers, verified by the test suite
cases/          golden test cases — add one without writing Python
benchmarks/     scaled input generators (chain/tree/clique/grid)
tests.py        127 tests: every shipped program and exercise answer is
                executed, a conformance suite runs every query through
                every applicable strategy, and a seeded fuzzer checks
                the same property on random programs
```

The code is part of the course: comments explain the algorithms as
they happen, and the lessons that introduce machinery end with an
*Under the hood* section reading the piece of the implementation they
used.

### How big is it, honestly

The evaluator is about 800 lines (`datalog.py`, up to the
command-line interface), the CLI, `--explain` and why-not another 500, and the eight satellite modules about
2,200. Call it 3.4k lines of toolkit and 1.4k of tests, roughly a
quarter of it commentary.

"Tiny" is a claim about the evaluator, and about each satellite module
singly: none of the eight exceeds 475 lines, which a test asserts. It is not a claim about
the repository, which is nine modules because it teaches nine things.

There is no dead code to golf away (checked); shrinking further means
deleting either a technique or an explanation.

## License

MIT.
