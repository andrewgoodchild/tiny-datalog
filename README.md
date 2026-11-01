# tiny-datalog

[![tests](https://github.com/andrewgoodchild/tiny-datalog/actions/workflows/ci.yml/badge.svg)](https://github.com/andrewgoodchild/tiny-datalog/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tiny-datalog)](https://pypi.org/project/tiny-datalog/)

**A Datalog engine whose core you can read in an afternoon, a course
that builds it up from nothing, and a module for every technique the
course teaches.**

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
python3 tests.py        # 429 tests, ~20s
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
[lesson 17](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/17-writing-rules.md) writes a lending policy badly
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
[Lesson 16](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/16-containment.md) covers the boundary.)

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
`containment.py` catches redundancy, integrity constraints catch a rule
set that breaks the policy stated another way, warnings catch the typo
that silently empties a relation, and `--explain` produces the
derivation somebody has to sign off on.

Two limits. An engine checks coherence, not intent: a rule set can pass
every check above and still be the wrong policy. And the trade only
pays when the rules genuinely outlive the query. For a one-off
question, or anything arithmetic-heavy, forty lines of ordinary code is
the better tool, and that covers most problems.

## What else you can ask it

The worked example above is one row of a table. The full version — 32
questions, each with the command that answers it and the lesson that
builds the machinery — is in
[getting started](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/getting-started.md), beside the reading
paths.

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
[Lesson 7](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/07-magic-sets.md) works through why.

Correctness is checked by a seeded differential fuzzer that generates
stratified programs, aggregates and integrity constraints included,
and demands that all five engines agree, on the answers and on the
counterexamples, with every query of a program sent to one engine (so
the tabled engines answer later queries from their table space); that
SLG matches the well-founded model on unstratified
ones, with and without subsumptive tabling; and that incremental
maintenance, bottom-up and in the tabled engines' table spaces,
matches recomputation under random updates. 400 programs
per run;
`TINY_DATALOG_FUZZ=3000 python3 tests.py DifferentialFuzzTests` soaks.

Answers are also checked against engines this repository did not write.
[`conformance/`](https://github.com/andrewgoodchild/tiny-datalog/tree/main/conformance)
runs the [datalog-conformance](https://pypi.org/project/datalog-conformance/)
corpus, harvested from Soufflé, Nemo and Crepe, through all five
strategies, and its defeasible theories, from SPINdle and the papers,
through `defeasible.py`: 195 cases pass. Every skip is named with its
reason: arithmetic and 10⁵-fact joins, which this course omits on
purpose, or cases written for a different logic.

And the tests themselves are checked: `benchmarks/mutate.py` makes
each one-line break a bug could make (a `<` for a `<=`, a dropped
`not`, a deleted statement) and runs the suite against each. At 0.7.0
the suite caught 91% of 3,322 such mutants. Most of the rest change
nothing a user could observe, such as a counter's starting value or a
default limit raised by one; the others are mainly CLI printing.

## Learning Datalog

`lessons/` is a complete course, no prior exposure assumed, every
example a runnable file, following the field's own history from 1977 to
the current research threads. The field's own recent lecture notes
observe that the literature advises people building Datalog engines
better than people trying to *use* one; this course does both halves
on purpose — sixteen lessons where the engine is the explanation, then
a lesson on authoring rules that survive review, one on a logic
built for rules with exceptions, and five where the engine goes to
work: [authorization](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/20-authorization.md),
[program analysis](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/21-program-analysis.md),
[knowledge graphs and the chase](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/22-knowledge-graphs.md),
[time and history](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/23-time.md),
and [memory for a language-model agent](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/24-memory.md).
And it is built to be
inherited: `git clone`, no dependencies, no hosted anything, and every
quoted transcript re-verified by CI — the exercises cannot rot. (For where each
technique ships — CodeQL, RDFox, Feldera, SNOMED and the rest —
[lesson 0](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/00-what-is-datalog.md) ends with the deployments.)
[lessons/getting-started.md](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/getting-started.md) has the titles
and the reading order, and
[lessons/glossary.md](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/glossary.md) defines every technical term
the course uses, and
[lessons/references.md](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/references.md) collects every work the
lessons cite.

Three of them teach things that are hard to find taught well anywhere
else, and they are the reason the course exists rather than just the
engine:

- **[Lesson 8](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/08-semirings.md)** proves that why-provenance
  cannot be specialised into derivation counts, with a program that
  prints the disproof: two facts with identical provenance and different
  counts. That settles "materialise provenance once, specialise later,"
  which is a real design-review question with a real answer.
- **[Lesson 16](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/16-containment.md)** shows that the containment
  test you need for query minimisation is the search already sitting in
  the core: `match` maps a rule body into a database,
  `find_homomorphism` maps a rule body into another rule body. Same
  backtracking, one level up.
- **[Lesson 4](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/04-closed-and-open-worlds.md)** contrasts the
  two reasoners in this repository, which disagree about what absence
  means, and leaves you with a habit: when you see `not`, ask whose
  authority says this is absent.

Every lesson ends with exercises, and every exercise has a worked answer
in `exercises/` — runnable where the answer is a program, and executed
by the test suite so the answers cannot rot. `cases/` lets anyone add a
regression test without writing Python.

## What this is not, and what is missing on purpose

Not an engine to build a product on. The bottom-up engines join by
nested loop with no join planning, stable-model search is exhaustive,
and evaluation starts from scratch, apart from `incremental.py` and
the tabled engines' incremental tabling. For real
workloads see Soufflé, clingo, RDFox or Feldera; for Datalog inside a
Python application, with arithmetic and queries over SQL databases,
see [pyDatalog](https://pypi.org/project/pyDatalog/).

Deliberate omissions, because saying why teaches more than lacking them
quietly:

- **Arithmetic.** `Z = X + 1` makes values nobody stated, so it can make
  a relation infinite, and the termination theorem goes with it.
  [Lesson 14](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/14-arithmetic.md) is the whole
  story, including what to do instead.
- **Indexes and join planning.** The bottom-up engines join every
  body by nested loop, left to right, so the algorithms stay
  one-screen readable. It is also why the magic-sets timing above goes
  the way it does. The only indexes are the ones `slg.py -s` builds
  for the call patterns it serves, the one `--explain` uses to find
  an earlier derivation, and the one `slg.py` keeps while it
  simplifies.
- **⊤ and role hierarchies** in the classifier — what ships is EL⊥
  (disjointness and unsatisfiability detection included). SNOMED needs
  ELH (EL plus role hierarchies) with right identities, which is what
  the ELK and Snorocket reasoners implement and this does not.
- **A REPL (interactive prompt).** Run a file, or call it from Python.

Aggregation used to be on this list;
[lesson 13](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/13-aggregation.md) is what promoting an omission
into a feature looks like, and
[lesson 15](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/15-tabling.md) goes a step further: the tabled
engines let `min` and `max` recurse, by answer subsumption, where
stratification refuses them. Comparisons (`<`, `<=`, `>`, `>=`, `=`,
`!=`) used to share arithmetic's entry. They check values and never
make them, so they can only filter, and lesson 14's own argument lets
them in; [lesson 23](https://github.com/andrewgoodchild/tiny-datalog/blob/main/lessons/23-time.md) puts them to work.

## Using it in your own project

The engine is on PyPI, with no dependencies beyond the standard library:

```sh
pip install tiny-datalog
```

```python
from tiny_datalog import run_program, explain

engine = run_program(open("supply-chain.dl").read())
for answer in engine.query("exposed(S, C)"):
    print(answer)                     # {'S': 'pkg0', 'C': 'cve_2026_0001'}
print("\n".join(explain(engine, "exposed", ("pkg0", "cve_2026_0001"))))
```

Facts can come straight from Python data (a CSV file, a database
query) instead of program text. Each row is checked as if it had been
parsed:

```python
rules = """
uses(X, Y) :- depends(X, Y).
uses(X, Z) :- depends(X, Y), uses(Y, Z).
exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).
"""
engine = run_program(rules, facts={
    "depends": [("app", "lib"), ("lib", "core")],
    "service": ["app"],                         # one-column rows may be bare
    "vulnerable": [("core", "cve_2026_0001")],
})
engine.query("exposed(S, C)")       # [{'S': 'app', 'C': 'cve_2026_0001'}]
```

A rule with no head is an integrity constraint, a situation that must
never arise. `engine.violations()` lists each broken one with its
counterexamples, and the command line prints them and exits with
status 3, under every engine (`--engine tabling` asks each constraint
as one more query):

```python
checked = run_program(rules + ":- exposed(S, C).", facts={
    "depends": [("app", "lib"), ("lib", "core")],
    "service": ["app"],
    "vulnerable": [("core", "cve_2026_0001")],
})
checked.violations()  # [(constraint, [{'S': 'app', 'C': 'cve_2026_0001'}])]
```

For agents, `skills/tiny-datalog/SKILL.md` is an Agent Skill that
teaches a coding agent the language and the habits (explain before
trusting, state properties as constraints); copy it into your agent's
skills directory.

The command-line interface installs too, as `tiny-datalog` (and
`tiny-datalog-semiring`, `-tabling`, `-slg`, `-incremental`, `-subsumption`,
`-containment`, `-defeasible`, `-prolog` for the other engines and the
extensions):

```sh
tiny-datalog -q 'exposed(S, C)' supply-chain.dl
```

The course material — lessons, programs, exercises — is not part of the
installed package; clone the repository for that.

## Layout

```
tiny_datalog/   the code you read, in three tiers:
  core.py       the common core — the language every module shares:
                AST, parser, safety checks, comparisons, stratification,
                matching, formatting, query helpers, warnings
 engines — five strategies, one answer (engines.py lists them):
  datalog.py    the base engine: semi-naive and naive bottom-up
                evaluation, aggregation, integrity constraints,
                --explain / why-not, --assume, the CLI
  magic.py      the magic-sets rewriting (a program-to-program pass)
  tabling.py    tabled top-down evaluation (iterative QSQR), and the
                front end both tabled engines share
  tablespace.py the table space both tabled engines keep through
                updates: incremental tabling, eager or lazy, and
                explanations read off the tables
  lattice.py    answer subsumption: recursion through min and max,
                for both tabled engines
  engines.py    the registry and the interface the five share (the
                fifth is SLG, from slg.py below, held to stratified
                programs)
 extensions — other questions asked of the same programs:
  semantics.py  grounding, stable models, the well-founded model
  slg.py        SLG resolution: the well-founded model, top-down
  semiring.py   semiring-valued evaluation (costs, counts, provenance,
                probabilities)
  incremental.py  insertions + DRed deletions over a live materialisation
  prolog.py     top-down SLD resolution with function symbols
  subsumption.py  KL-ONE-style EL classifier, compiled to Datalog
  containment.py  query containment and minimisation by homomorphism
  defeasible.py   defeasible logic: exceptions, priorities, defeaters
  chase.py      existential rules: the chase, labelled nulls, weak
                acyclicity
*.py            three-line launchers, so `python3 datalog.py ...` works
                straight from a checkout with nothing installed
programs/       teaching programs, named for what they model; each
                lesson says which ones it runs
lessons/        getting started, glossary, and lessons 0–24
exercises/      worked answers, verified by the test suite
cases/          golden test cases — add one without writing Python
skills/         an Agent Skill that teaches coding agents to use the engine
conformance/    the external datalog-conformance corpus (Soufflé, Nemo,
                Crepe, SPINdle), run against every evaluation strategy
benchmarks/     scaled input generators (chain/tree/clique/grid, an EL
                ontology, and the N-queens puzzle), and mutate.py,
                which breaks the code one line at a time to measure
                how much of it the tests would notice (91% at 0.7.0)
tests.py        429 tests: every shipped program and exercise answer is
                executed, a conformance suite runs every query through
                every engine that handles it, and a seeded fuzzer checks
                the same property on random programs
```

The code is part of the course: comments explain the algorithms as
they happen, and the lessons that introduce machinery end with an
*Under the hood* section reading the piece of the implementation they
used.

### How big is it, honestly

This project started as an attempt at a tiny implementation of
Datalog, small enough to read in an afternoon. It grew with the
course. Each lesson that taught a new technique — magic sets, stable models,
semirings, incremental maintenance, tabling, SLG resolution, subsumption, containment,
defeasible logic, the chase — brought a module to run it, and the repository is
now several thousand lines. The core idea stayed small, and the code
is laid out so you can still read just that: the common core and the
base engine, below, are the original tiny Datalog. Everything else is
an engine or extension you can take one lesson at a time.

Measured in lines, comments, docstrings and blank lines included:

| Tier | Lines |
|---|---|
| the common core (`core.py`: the language, evaluating nothing; about 270 of these lines arrived with comparisons, constraints, value checks and the warnings) | 1,057 |
| the base engine's evaluator (`datalog.py` up to its CLI section: the module docstring, the import list that re-exports the core, `Program`, `Engine`, aggregation folding, `run_program`) | 423 |
| `--explain`, why-not, constraint reports, `--assume`, printing and the CLI (the rest of `datalog.py`) | 649 |
| the other pluggable engines: magic sets (`magic.py`) and tabling (`tabling.py`, with `tablespace.py` and `lattice.py`, the incremental tabling, explanations and answer subsumption both tabled engines share), plus the `engines.py` registry (naive evaluation is a flag on the base engine; the fifth engine, SLG, is counted with the extensions) | 1,469 |
| the nine extensions | 3,555 |

So the smallest complete Datalog system here — parse, check, stratify,
evaluate semi-naively — is the core plus the evaluator, about 1,500
lines. All of it is 7.2k lines of toolkit (every module but the
re-export list in `__init__.py`), roughly a quarter of it commentary,
and 5.2k of tests.

"Tiny" is a claim about that core and evaluator, and about each module
built on them singly: none of the fourteen (`magic.py`, `tabling.py`,
`tablespace.py`, `lattice.py`, `engines.py` and the nine extensions)
exceeds 500 lines, except `slg.py`, allowed 700 because it is tabling
plus a scheduler. A test asserts the limits. It is not a
claim about the repository, which is a dozen modules because it
teaches a dozen things.

There is no dead code to golf away (checked); shrinking further means
deleting either a technique or an explanation.

## License

MIT.
