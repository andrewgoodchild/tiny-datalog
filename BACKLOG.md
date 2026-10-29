# Backlog

Loose ends: features the course has left out, refused with an error, or
handed to the reader as an exercise. Most of them were left out on
purpose, and the lesson cited says why. Taking one on usually means
updating that lesson's argument as well as the code.

## Tooling

- **A REPL (interactive prompt).** The README lists it as a deliberate
  omission: "Run a file, or call it from Python." Nothing reads
  interactive input today. It could load a program, accept facts, rules
  and queries line by line, and switch between engines.
- **A step-through debugger.** [Lesson 15](lessons/15-tabling.md)
  ("The other reason top-down survives") says that turning
  `tabling.py` into a stepper "is an exercise in attaching a prompt to
  `_prove`." It shares most of its machinery with the REPL.
- **Indexes and join planning.** Every join is a nested loop and runs
  strictly left to right (README, [lesson 17](lessons/17-writing-rules.md)).
  This is also why the magic-sets timing in the README comes out the
  way it does.

## Tabling

SLG resolution is done: `slg.py` (lesson 15) has suspend and resume,
completion detection, delay and simplify, and answer completion, and is
checked against `semantics.py`'s well-founded model on random
unstratified programs. It is also the fifth engine in `engines.py`
(`datalog.py --engine slg`), held to stratified programs, so the
conformance suite and the external corpus run through it. `slg.py` is
about 460 lines of its 500, so most items below need room made first.
Still open:

- **Tabled aggregation**, in both `tabling.py` and `slg.py`. Refused:
  "tabled aggregation is not implemented here — use datalog.py".
- **A table space shared across queries.** Tables reset on every query
  (exercise 3).
- **Integrity constraints.** Refused by both: only the base engine
  checks them.
- **Local scheduling in `slg.py`.** It has XSB's completion stack,
  but a single global work queue, so a group can only complete once
  *all* work has run out. XSB schedules one subgoal's work at a time and
  completes groups as soon as their own work is done, which also frees
  memory earlier. (Facts-only tables already complete at once.)
- **A step-through debugger** on `slg.py`: its parked frames are
  already plain data, so stepping them may be easier than on
  `tabling.py`'s generators.
- **Subsumptive tabling.** Both engines start a table for every
  distinct call pattern (variant tabling), so `path(a, X)` gets its own
  table even when `path(X, Y)` is already complete. XSB can answer the
  specific call from the general table instead. Lesson 15's queens
  table count is where the saving would show.
- **Incremental tabling.** Tables are thrown away when facts change.
  Keeping them, and invalidating only the tables that depend on the
  changed facts, is what `incremental.py` does for bottom-up
  evaluation ([lesson 10](lessons/10-incremental.md)), and what XSB
  calls incremental tabling.
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
