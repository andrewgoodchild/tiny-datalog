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
and evaluation is the working-out of all consequences.** Three properties
define it:

1. **Declarative** — you never say *how* to compute (no loops, no
   ordering); the engine picks the strategy.
2. **Recursive** — reachability, hierarchies, and dependency closures are
   native, not bolted on.
3. **Terminating** — every Datalog program finishes. Always. This is a
   theorem, not a convention, and Lesson 9 shows the price paid for it.

If you know SQL: Datalog is roughly "SELECT–JOIN plus real recursion,
minus the ceremony." If you know Prolog: Datalog is Prolog without
function symbols, evaluated bottom-up, with termination guaranteed.

For a program that looks like actual work rather than a textbook
figure, read `programs/00-eligibility.dl` — a benefits policy with an
exemption clause, which the engine can both evaluate and *justify*
(`--explain 'eligible(bob)'`). You will be able to write it yourself
after lesson 3, and to explain how `--explain` works after lesson 11.

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
theorem: monotone Datalog is exactly what needs no coordination.

**The present (2020s).** The active research threads: **semiring
provenance** (one program computing costs, counts, and evidence —
Lesson 6), **incremental computation** (DBSP and differential dataflow —
Lesson 8's DRed is their ancestor), **neurosymbolic AI** (Scallop:
differentiable Datalog inside neural networks — Lesson 7 is the on-ramp),
equality saturation (egglog), and verification via constrained Horn
clauses (Lesson 9's closing note).

## Who invented Datalog?

Datalog has many parents but one namer. The mathematical object —
Horn-clause logic with function symbols removed, read over a database —
crystallised from several hands: Maarten van Emden and Robert Kowalski
gave logic programs their least-model semantics in 1976 (Kowalski is now
professor emeritus at Imperial College London, still writing on
computational logic), and the field itself was convened by **Hervé
Gallaire** and **Jack Minker**, whose 1977 workshop and 1978 book *Logic
and Data Bases* made "logic meets databases" a discipline. Gallaire went
on to senior research leadership at Xerox and later retired.
Minker spent his career at the University of Maryland and was equally
renowned outside computer science as a human-rights advocate for
imprisoned Soviet scientists; he died in 2021.

The *name* — and much of the language's identity as a thing distinct
from Prolog — is generally credited to **David Maier**, who coined
"Datalog" in the early 1980s. Maier is one of database theory's central
figures: author of *The Theory of Relational Databases* (1983),
co-author with **David S. Warren** of *Computing with Logic* (1988), a
builder of the GemStone object database and of stream-processing
systems. After Stony Brook and the Oregon Graduate Institute he moved
to Portland State University in Oregon, where he is the Maseeh Professor
of Emerging Technologies. In 2018 he co-wrote, with
Warren and colleagues, the retrospective *"Datalog: Concepts, History,
and Outlook"* — the definitive account of the language's life, by the
people who lived it. Warren, for his part, built XSB — the tabling
engine that kept the well-founded semantics alive through the winter
years (Act 3 above) — and is professor emeritus at Stony Brook
University.

So when this course's Lesson 9 shows you the function-symbol boundary,
you are looking at the exact line Maier drew when he needed a name for
"Prolog's logic, a database's discipline."

## Why any of this matters in a world of LLMs

A fair question: if a language model can answer questions about your
data, why learn a sixty-year-old logic formalism? Four reasons, each
sharper *because* of LLMs, not despite them.

**Soundness is not a vibe.** An LLM's answer is a plausibility; a
Datalog derivation is a proof. When the conclusion must actually follow
— access control, financial eligibility, safety interlocks, static
analysis of code — "very likely correct" is a category error. The
emerging production pattern is LLM-as-translator, solver-as-reasoner:
the model turns a question into rules and facts, the engine does the
inference, and every answer is exactly as trustworthy as the inputs.

**Paradox detection, not paradox smoothing.** This repository's café
paradox (Lesson 5) is the demonstration: a policy that sounds sensible
in English but is formally self-contradictory. Ask an LLM and you get a
fluent essay that papers over the contradiction. Ask the engine and you
get a refusal that *names the cycle* — and the well-founded model
pinpoints exactly which individual the policy breaks on. Systems that
matter need the second behaviour.

**Provenance is the answer to hallucination.** Lesson 6's
why-provenance computes, for every conclusion, the minimal sets of base
facts that support it — citations that cannot be invented, because they
fall out of the derivation itself. Retrieval-augmented LLM systems
approximate this; semiring Datalog simply has it.

**The interface problem is solved — from the other side.** What killed
deductive databases commercially in the 1990s was that ordinary users
wouldn't write logic. LLMs are startlingly good at writing Datalog: the
translation layer that was the field's fatal weakness is now nearly
free, while the guarantees that were always its strength have become the
scarce resource. The neurosymbolic thread (Lesson 7) goes further and
puts the logic *inside* the learning loop, gradients and all.

The one-line version: **LLMs generate; logic engines guarantee.**
Systems that need both — and increasingly, that is most interesting
systems — need people who understand the guarantee side.

## Where each idea earns its living

None of this course is purely academic, but the commercial density
varies. The honest map, one line per lesson:

| Lesson | Technique | Who ships it |
|---|---|---|
| 1 | rules = joins | every RDBMS; the query languages of Datomic and XTDB; CodeQL queries |
| 2 | recursion, semi-naive | SQL `WITH RECURSIVE`; Soufflé and CodeQL static analysis; the inner loop of every Datalog engine |
| 3 | stratified negation | Soufflé and RDFox ship exactly this dialect; eligibility, access-control, and compliance rule engines |
| 4 | magic sets | Soufflé's transform; LogicBlox's demand transformation; the predicate-pushdown instinct in every SQL optimizer |
| 5 | stable models, WFS | clingo product configurators and schedulers (Siemens); XSB-lineage compliance systems; policy consistency checking |
| 6 | semirings, provenance | data-lineage and audit tooling; Soufflé's provenance debugger; min-plus routing; RelationalAI's engine |
| 7 | Viterbi, probabilistic | Viterbi decodes every phone call; neurosymbolic AI (Scallop) is the research-to-startup frontier |
| 8 | incremental, DRed | Materialize, Feldera, Snowflake dynamic tables; RDFox incremental reasoning — a live hiring market |
| 9 | Horn clauses, SLD | Prolog's industrial niches (Watson's parser); constrained-Horn-clause verification at cloud providers |
| 10 | subsumption | the EL family under ELK/Snorocket, classifying SNOMED CT for health records; OWL reasoners in enterprise knowledge graphs |
| 11 | engine internals | the kernels of Soufflé, RDFox, RelationalAI — what their teams hire for |
| 12 | aggregation | GROUP BY is the warehouse workload; recursive aggregation is the current competitive frontier |
| 13 | tabling | XSB, three decades in production; SWI-Prolog ships tabling; memoisation, generalised |

The nichest rows are 5 and 7 — real deployments, smaller markets.
Everything else is core data-industry machinery wearing lesson numbers.

## How this course follows the history

| Era | Idea | Where here |
|---|---|---|
| 1977–1985 | facts, rules, joins, recursion, semi-naive | Lessons 1–2 · `datalog.py` |
| 1986 | magic sets | Lesson 4 · `magic.py` |
| 1988–1991 | stratification; stable models; well-founded | Lessons 3 & 5 · `semantics.py` |
| 2007– | provenance semirings, recursive aggregation | Lesson 6 · `semiring.py` |
| 2020s | probabilistic / neurosymbolic | Lesson 7 |
| 1993 → 2023 | DRed → differential dataflow → DBSP | Lesson 8 · `incremental.py` |
| 1965–1972 | Horn clauses, resolution, Prolog | Lesson 9 · `prolog.py` |
| 1978 → today | KL-ONE → description logics → OWL / SNOMED | Lesson 10 · `subsumption.py` |
| 1990s → today | recursive aggregation; SLG tabling (XSB) | Lessons 12–13 · `tabling.py` |

The repository is small on purpose — every algorithm named above is
implemented in readable standard-library Python, and every example in
every lesson is a file you can run.

## Further reading, and one road not taken

The course's mathematics is **lattice theory** (fixpoints — Lesson 2),
**model theory** (homomorphisms and containment — Lesson 14), and
**universal algebra** (semirings and their quotients — Lesson 6). Those
are the tools the field actually reaches for, and every result in these
lessons is stated in them.

A reader arriving from category theory will notice that much of this
*can* be recast categorically: instances and homomorphisms form a
category, `lfp(T_P)` is an initial algebra, semiring specialisation is
a functor. All true, and — for classical Datalog — none of it doing
work the lattice-and-semiring toolkit wasn't already doing. Nothing in
`datalog.py` would be different. It is worth saying plainly, because
the vocabulary is attractive enough to mistake for content.

Where categorical machinery genuinely earns its place is one step
outside this repository: at **existential rules** (Datalog±, the
chase), where the chase is a left Kan extension, and at **functorial
data migration** (schemas as categories, instances as functors,
migration as Kan extensions — CQL and the Topos Institute line). Both
concern the fragment this engine deliberately does not implement, and
both are live research rather than settled technique. If you add
existentials, that is the road; until then, it is a signpost.

Start here: [getting started](getting-started.md), then
[Lesson 1](01-first-steps.md).
