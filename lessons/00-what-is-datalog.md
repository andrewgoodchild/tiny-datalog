# Lesson 0 — What is Datalog, and why should you care?

Suppose your database has a table of who reports to whom, and you want
everyone in Alice's reporting chain — her reports, their reports, all the
way down. In SQL that's a recursive common table expression most
developers have to look up the syntax for. In Datalog it is the problem's
own logical structure, and nothing else:

```prolog
manages(alice, bob).
manages(bob, carol).

chain(X, Y) :- manages(X, Y).
chain(X, Z) :- manages(X, Y), chain(Y, Z).
```

That's a complete program. `:-` reads "if", the comma reads "and",
capital letters are variables. Run it and the engine derives every
`chain` fact the rules imply — including `chain(alice, carol)`, which no
one wrote down.

**Datalog is a query language where you state what follows from what,
and evaluation is the working-out of all consequences.** The README
names three properties; here is what each one costs and buys:

1. **Declarative**. You never say *how* to compute (no loops, no
   ordering); the engine picks the strategy.
2. **Recursive** — reachability, hierarchies, and dependency closures are
   native, not bolted on.
3. **Terminating**, every Datalog program finishes. Always. This is a
   theorem, not a convention, and Lesson 10 shows the price paid for it.

If you know SQL: Datalog is roughly "SELECT–JOIN plus real recursion,
minus the ceremony." If you know Prolog: Datalog is Prolog without
function symbols, evaluated bottom-up, with termination guaranteed.

For a program that looks like actual work rather than a textbook
figure, read `programs/eligibility.dl`: a benefits policy with an
exemption clause, which the engine can both evaluate and *justify*
(`--explain 'eligible(bob)'`). You will be able to write it yourself
after lesson 3, and to explain how `--explain` works after lesson 2's
Under the hood section.

## A short history, in five acts

**Roots (1965–1977).** Automated reasoning begins in earnest with
Robinson's resolution principle (1965); Prolog (1972, Colmerauer and
Kowalski) turns Horn-clause logic into a programming language. The 1977
*Logic and Databases* workshop asks the pivotal question: what happens
when logic meets the relational database?

**The golden age (1980s).** "Datalog" gets its name, and the
deductive-database community works out the canon this repository
implements: bottom-up **semi-naive evaluation** (don't rederive what you
already know), **magic sets** (1986 — make bottom-up as goal-directed as
Prolog), and **stratified negation** (give "not" a safe, layered
meaning). When stratification proved too narrow, the semantics race of
1988–1991 produced the two lasting answers: **stable models** (Gelfond
and Lifschitz, 1988) and the **well-founded semantics** (Van Gelder,
Ross, Schlipf, 1991).

**The winter (1990s).** Deductive databases fail commercially. SQL:1999
absorbs a weak form of recursion (`WITH RECURSIVE`) and the field is
declared a theoretician's playground. Two quiet survivors matter later:
the stable-model camp becomes **answer set programming** (today's
clingo), and XSB keeps the well-founded semantics running in practice.

**The renaissance (2000s–2010s).** Datalog returns because other fields
discover their problems *are* Datalog. Program analysis leads the way —
points-to analysis is mutually recursive rules, and the line runs from
bddbddb (2004) and Doop (2009) to Soufflé and GitHub's **CodeQL**,
probably the most widely deployed Datalog on earth. Databases speak it
again (Datomic, 2012; RDFox; LogicBlox, whose engine gave database theory
worst-case optimal joins). Distributed-systems theory gets the CALM
theorem (Consistency As Logical Monotonicity): monotone Datalog is
exactly what needs no coordination.

**The present (2020s).** The active research threads: **semiring
provenance** (one program computing costs, counts, and evidence —
Lesson 7), **incremental computation** (DBSP and differential dataflow —
Lesson 9's DRed is their ancestor), **neurosymbolic AI** (Scallop:
differentiable Datalog inside neural networks — Lesson 8 is the on-ramp),
equality saturation (egglog), and verification via constrained Horn
clauses (Lesson 10's closing note).

## Who invented Datalog?

Datalog has many parents but one namer. The mathematical object —
Horn-clause logic with function symbols removed, read over a database —
crystallised from several hands: Maarten van Emden and Robert Kowalski
gave logic programs their least-model semantics in 1976, and the field
itself was convened by **Hervé Gallaire** and **Jack Minker**, whose
1977 workshop and 1978 book *Logic and Data Bases* made "logic meets
databases" a discipline.

The *name*, and much of the language's identity as a thing distinct
from Prolog — is generally credited to **David Maier**, who coined
"Datalog" in the early 1980s. Maier is one of database theory's central
figures: author of *The Theory of Relational Databases* (1983),
co-author with **David S. Warren** of *Computing with Logic* (1988),
and a builder of the GemStone object database. In 2018 he co-wrote,
with Warren and colleagues, the retrospective *"Datalog: Concepts,
History, and Outlook"*: the definitive account of the language's life,
by people who lived it. Warren built XSB, the tabling engine that kept
the well-founded semantics alive through the winter years of Act 3.

So when this course's Lesson 10 shows you the function-symbol boundary,
you are looking at the exact line Maier drew when he needed a name for
"Prolog's logic, a database's discipline."

## Why any of this matters in a world of LLMs

There is a trap here, and it is worth walking into deliberately once so
you never do it again.

The obvious test is to hand a language model a logic puzzle and watch it
fail. It is the oldest story in science fiction: feed the machine a
paradox, watch it seize. That story assumes the machine is a deductive
system, in which a contradiction propagates until something breaks. A
language model has no propagation: a contradiction is just more text,
and it glides past. **You cannot crash it with a paradox because there
is no inference engine in there to crash.**

It also assumes models are weak at logic, and they are not. Logic
puzzles are cheap to verify, which makes them ideal reinforcement
learning targets, so the labs have trained on them hard. On top of that,
the classic paradoxes are among the most written-about objects in the
Western canon: the café paradox in Lesson 5 *is* the barber paradox
*is* Russell's paradox, discussed in logic textbooks for a century. Hand
a frontier model that puzzle and it will do fine. It was never a probe.

The deeper problem with the test is that **it cannot distinguish
retrieval from reasoning.** Whatever a model does with a familiar
puzzle tells you nothing about what it does with an unfamiliar one, and
both produce identical-looking transcripts.

So what *is* the case for this material?

**Verification.** It is what formal methods have always been for. A
model gives you an answer plus an explanation, where the explanation is
a separate artifact — fluent, plausible, and generated by the process
that also invents citations. An engine gives you an answer whose
derivation *is* the computation. When it reports *no stable model
exists*, that is a property of your rules, true of rules nobody has
ever written; when a model reports it, you cannot tell from one test
whether you got reasoning or recall.

There is also a complexity result worth carrying, because it says where
the limit is rather than guessing at it. Directed graph reachability is
NL-complete (as hard as any problem a nondeterministic machine solves
in logarithmic space) and Horn-clause satisfiability, which is what
evaluating
Datalog rules *is* — is P-complete. Merrill and Sabharwal (ICLR 2024)
prove that transformers with a linear number of chain-of-thought steps
can decide neither, naming both explicitly. Doing this kind of
reasoning *in tokens* is not a training gap that will close; it is
outside the shape of the computation. Which is why models sensibly
write code instead, and why the README's argument is about what that
code should be rather than about whether models can reason.

All of which inverts where the danger lies. Logic puzzles are the *safest*
place to probe a model, because they are exactly where cheap
verification made training effective. The risk sits wherever a
confident answer cannot be checked in under a minute, and that is a
much larger territory than the one science fiction warned us about.

## How this course follows the history

| Era | Idea | Where here |
|---|---|---|
| 1977–1985 | facts, rules, joins, recursion, semi-naive | Lessons 1–2 · `datalog.py` |
| 1986 | magic sets | Lesson 6 · `magic.py` |
| 1988–1991 | stratification; stable models; well-founded | Lessons 3 & 5 · `semantics.py` |
| 2007– | provenance semirings, recursive aggregation | Lesson 7 · `semiring.py` |
| 2020s | probabilistic / neurosymbolic | Lesson 8 |
| 1993 → 2023 | DRed → differential dataflow → DBSP | Lesson 9 · `incremental.py` |
| 1965–1972 | Horn clauses, resolution, Prolog | Lesson 10 · `prolog.py` |
| 1977 | conjunctive-query containment (Chandra–Merlin) | Lesson 14 · `containment.py` |
| 1978 → today | KL-ONE → description logics → OWL / SNOMED CT | Lesson 11 · `subsumption.py` |
| throughout | closed vs open worlds — what absence means | Lesson 4 |
| the practice | authoring rules others must review | Lesson 15 |
| the mathematics | what the course is made of, and the road not taken | Lesson 16 |
| 1990s → today | recursive aggregation; SLG tabling, the resolution strategy XSB implements | Lessons 12–13 · `tabling.py` |

The repository is small on purpose, every algorithm named above is
implemented in readable standard-library Python, and every example in
every lesson is a file you can run.

## Five places Datalog earns its living

Not toy deployments — systems you can check, each mapped to the lesson
that teaches its core idea.

1. **Code security at scale.** Semmle's QL — an object-oriented Datalog
   for "analyzing source code to detect security vulnerabilities" —
   became GitHub's **CodeQL**, which scans code across GitHub today.
   The **Soufflé** dialect writes pointer analyses for Java and
   control-flow analyses for Scheme. Recursion over a program's
   dependency graph is Lessons 2 and 6's material.
2. **Databases that speak it.** **Datomic** uses Datalog as its query
   language on a distributed database; **LogicBlox** ran web-based
   retail planning and insurance applications on it; and the **magic
   sets** algorithm — Lesson 6 — is implemented inside IBM's DB2.
3. **Knowledge graphs and medical terminology.** **RDFox** is a
   main-memory triple store built on Datalog reasoning, with Lesson 9's
   Backward/Forward as its deletion algorithm. And every release of
   **SNOMED CT**, the ~350,000-concept clinical terminology behind
   electronic health records, is classified by EL reasoners running the
   saturation calculus Lesson 11 compiles to Datalog.
4. **Industrial scheduling and configuration.** Answer set programming
   — Lesson 5's stable models, industrialised — was first applied to
   **product configuration** in 1998 (Soininen and Niemelä), and
   solves **real-world train scheduling** (routing, scheduling and
   optimisation together) with clingo's hybrid extensions (Abels et
   al., arXiv 2003.08598).
5. **Program verification.** Compilers and verifiers discharge safety
   questions as **constrained Horn clauses** — Lesson 10's clause shape
   plus arithmetic — solved by engines like Z3's Spacer, with an annual
   solver competition (CHC-COMP) to keep everyone honest.

The pattern across all five: small rule sets, large or changing data,
and answers someone must be able to trust or audit — exactly the
territory the README stakes out.

For everything else, there is [the glossary](glossary.md), and for the
mathematically curious there is [Lesson 16](16-category-theory.md) —
what the course's mathematics actually is, and why the categorical
recasting of it was a road deliberately not taken.

## What this repository can answer

Every row runs against the shipped programs — no dependencies, no
install step, Python 3.9+. A question, the command that answers it,
and the lesson that builds the machinery:

| Question | Command | Lesson |
|---|---|---|
| What follows from these facts and rules? | `python3 datalog.py programs/family.dl` | [1](01-first-steps.md) |
| What's reachable, at any depth? | `python3 datalog.py --trace programs/reachability.dl` | [2](02-recursion.md) |
| What holds *unless* something else does? | `python3 datalog.py programs/tweety.dl` | [3](03-negation.md) |
| Answer just this query — don't compute everything | `python3 datalog.py --magic -q 'path(n5, X)' programs/reachability.dl` | [6](06-magic-sets.md) |
| Is this rule set self-contradictory? | `python3 datalog.py --models programs/eligibility-paradox.dl` | [5](05-beyond-stratification.md) |
| Why did you conclude that? | `python3 datalog.py --explain 'eligible(bob)' programs/eligibility.dl` | [1](01-first-steps.md), [2](02-recursion.md) |
| Which facts does the conclusion rest on? | `python3 semiring.py -s why programs/routes.dl` | [7](07-semirings.md) |
| What's the cheapest route? How many ways? | `python3 semiring.py -s minplus programs/routes.dl` | [7](07-semirings.md) |
| How likely is it? | `python3 semiring.py -s viterbi programs/prob-reach.dl` | [8](08-probabilistic.md) |
| The data changed — what changed in the answers? | `python3 incremental.py programs/dred-graph.dl -u 'edge(n3, n4)~.'` | [9](09-incremental.md) |
| How many, how much, largest? | `python3 datalog.py programs/spending.dl` | [12](12-aggregation.md) |
| Answer a goal top-down, even left-recursive | `python3 tabling.py programs/left-recursive.dl -q 'ancestor(abe, X)'` | [13](13-tabling.md) |
| What if I allow function symbols, and lose termination? | `python3 prolog.py programs/peano.pl -q 'add(X, Y, s(s(zero)))'` | [10](10-horn-clauses.md) |
| What do these definitions entail about each other? | `python3 subsumption.py programs/family-ontology.dl` | [11](11-kl-one-subsumption.md) |
| Are these two queries the same query? | `python3 containment.py programs/minimise.dl` | [14](14-containment.md) |
| Does absence mean false, or just unrecorded? | `python3 datalog.py programs/missing-data.dl` | [4](04-closed-and-open-worlds.md) |
| How do I write rules someone else can sign off? | `python3 datalog.py --explain 'may_borrow(iris)' programs/lending.dl` | [15](15-writing-rules.md) |

Provenance, in full:

```
$ python3 semiring.py -s why -q 'path(a, d)' programs/routes.dl
Semiring: why   (fixpoint after 5 rounds)
?- path(a, d)
   path(a, d) = {edge(a, b), edge(b, c), edge(c, d)} | {edge(a, b), edge(b, d)} | {edge(a, c), edge(c, d)}
   (1 answer)
```

Three independent derivations, each a minimal set of base facts. Remove
one fact from a witness and that witness fails; remove all three and the
conclusion goes away. That is an audit trail computed rather than
narrated.

Start here: [getting started](getting-started.md), then
[Lesson 1](01-first-steps.md).
