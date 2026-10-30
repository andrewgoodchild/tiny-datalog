# Backlog

Loose ends: features the course has left out, refused with an error, or
handed to the reader as an exercise. Most of them were left out on
purpose, and the lesson cited says why. Taking one on usually means
updating that lesson's argument as well as the code.

## Tooling

Parked for now: the REPL and both debuggers below.

- **A REPL (interactive prompt).** The README lists it as a deliberate
  omission: "Run a file, or call it from Python." Nothing reads
  interactive input today. It could load a program, accept facts, rules
  and queries line by line, and switch between engines.
- **A step-through debugger.** [Lesson 15](lessons/15-tabling.md)
  ("The other reason top-down survives") says that turning
  `tabling.py` into a stepper "is an exercise in attaching a prompt to
  `_prove`." It shares most of its machinery with the REPL.
- **Mutation testing in CI.** `benchmarks/mutate.py` takes hours for
  the whole package, so it runs by hand, not in CI. At 0.7.0 it caught
  91%; most survivors are equivalent mutants or CLI printing. Running
  it on just the modules a pull request touches would fit in CI.
- **Indexes and join planning.** Every join is a nested loop and runs
  strictly left to right (README, [lesson 17](lessons/17-writing-rules.md)).
  This is also why the magic-sets timing in the README comes out the
  way it does.

## Tabling

Done: `slg.py` (lesson 15) has suspend and resume, completion by
stack, local scheduling (a group completes as soon as its own work is
done), delay and simplify, and answer completion. It is checked
against `semantics.py`'s well-founded model on random unstratified
programs, and it is the fifth engine in `engines.py`
(`datalog.py --engine slg`). Both tabled engines table aggregation,
through an auxiliary table per aggregate rule, and `slg.py -s` adds
subsumptive tabling from complete tables. Both keep their tables
between queries (a table space), keep them through a change to the
facts by rebuilding only the tables that read it, stopping at one
that comes out unchanged (`apply`, `-u`: incremental tabling), and check integrity constraints, each as one
more query. The two tabled modules have higher line limits than the
other modules' 500: 700 for `slg.py`, 600 for `tabling.py`. Still
open:

- **Subsumption from incomplete tables, and answer indexing.**
  `-s` reads only complete tables, and only a ground call gets a
  direct lookup; any other served call scans the general table, which
  is why `-s` makes eight queens slower. XSB's answer tries index
  every pattern and let a call consume from an incomplete general
  table (lesson 15, exercise 6).
- **Lazy rebuilding.** `apply` rebuilds every reached table at once,
  even one no later query asks for. XSB marks them invalid and rebuilds
  one only when a query reaches it, which would also let a query read
  a large table space after a small update without paying for the
  rest.
- **Re-pushing an answer that becomes true.** An answer returned to
  its consumers while still conditional is not sent again when it
  later turns true, so they keep a delayed reference to it until
  simplification. The answers are correct, but some `not` calls are
  delayed that could have been decided. Fixing it changes the work
  counters lesson 15 quotes.
- **A simplification worklist.** `_simplify` rescans every
  conditional answer on each pass, and `_drop_unfounded` rescans until
  nothing grows. Indexing answers by the delayed literals they mention
  would make both linear. No program in the course is slow enough here
  to show it.
- **A step-through debugger** on `slg.py` (parked, with the REPL):
  its suspended frames are already plain data, so stepping them may be
  easier than on `tabling.py`'s generators.

## Negation, aggregation and constraints in the other engines

- **Incremental maintenance under negation and aggregation**
  (`incremental.py`, [lesson 10](lessons/10-incremental.md)). It needs
  bookkeeping for each stratum. Such programs are refused today.
- **Semirings and negation** (`semiring.py`, [lesson 8](lessons/08-semirings.md)).
  It is unclear what `not p` means when p carries a cost or a witness
  set. Positive programs only.
- **Semi-naive evaluation for semirings.** Deltas of semiring values
  need subtraction, which semirings don't have. That is the DBSP insight
  that lesson 10 discusses.
- **Stable-model and well-founded semantics with aggregates**
  (`semantics.py`). Refused as "still debated in the literature".
- **Smarter stable-model search.** The search enumerates every
  candidate model. [Lesson 5](lessons/05-beyond-stratification.md)
  points to clingo's conflict-driven learning as the real approach.
- **The chase** (`chase.py`, [lesson 22](lessons/22-knowledge-graphs.md))
  refuses negation, aggregates, comparisons and integrity constraints.

## Language limits

- **Arithmetic** (`Z = X + 1`). [Lesson 14](lessons/14-arithmetic.md)
  explains why it is left out: it can make a relation infinite. A
  bounded or guarded form could be a later lesson, as comparisons were.
- **The Prolog interpreter** (`prolog.py`) has no cut, no arithmetic and
  no I/O. Its negation as failure is a sub-proof with a depth bound.

## Description logic classifier

From [lesson 12](lessons/12-kl-one-subsumption.md), what ships is EL⊥.
Still missing:

- ⊤ (a universal concept);
- role hierarchies (`subrole(...)` is refused loudly), role chains and
  right identities. ELH with right identities is what SNOMED CT needs,
  and what ELK and Snorocket implement;
- nominals and datatypes;
- an ABox: the classifier reasons about definitions, never about
  individuals.

## Smaller threads

- **Probabilistic inference beyond enumeration.** Exact probabilities
  come from enumerating every possible world
  (`exercises/09-exact-prob.py`). There is no knowledge compilation and
  no sampling ([lesson 9](lessons/09-probabilistic.md)).

## New terrain

Where modern Datalog engines have gone that the course has not. The
first two would each remove a limitation the course already admits.

- **Worst-case optimal joins** (Leapfrog Triejoin, Generic Join). Any
  plan of pairwise joins can be asymptotically worse than optimal on a
  cyclic query such as a triangle; these join every relation at once,
  one variable at a time. LogicBlox and RelationalAI are built on them.
  This is the answer to the nested-loop joins under "Tooling", and a
  small version fits in a few hundred lines.
- **Datalog with lattices** (Flix, Ascent, Datafun). Recursion through
  monotone aggregates such as shortest path, or interval analysis over
  a lattice, which stratified aggregation ([lesson 13](lessons/13-aggregation.md))
  refuses. It is semirings ([lesson 8](lessons/08-semirings.md)) in the
  form program analysis uses.
- **Egglog: Datalog and e-graphs.** Datalog combined with equality
  saturation, for compiler optimisation and term rewriting. The most
  active new area.
- **Differential and streaming Datalog** (Differential Dataflow, DBSP,
  Feldera). Incremental maintenance with negation and aggregation, the
  item under "Negation, aggregation and constraints" above, done as
  dataflow over changes with weights.
- **Compiling Datalog** (Soufflé). Rules turned into specialised code
  instead of interpreted; a lesson could generate Python for each rule
  and measure the difference.
- **Neural and differentiable Datalog** (Scallop, DeepProbLog).
  Provenance semirings with gradients, next to lessons 8 and 9.
- **Warded Datalog±** (Vadalog). The decidable frontier of the
  existential rules that the chase ([lesson 22](lessons/22-knowledge-graphs.md))
  starts on.
- **Distributed and parallel evaluation** (BigDatalog, RecStep). Mostly
  engineering, so the least suited to this course.
