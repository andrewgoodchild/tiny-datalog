# Lesson 11 — Under the hood: how this engine is built

Ten lessons used the engine; this one reads it. Everything is plain
Python with no dependencies, written to be read — and the code's own
comments carry much of the story, so this lesson is a map, not a
paraphrase.

| File | What it implements | Taught in |
|---|---|---|
| `datalog.py` | AST, parser, safety, stratification, semi-naive engine, CLI | Lessons 1–3 |
| `magic.py` | the magic-sets rewriting | Lesson 4 |
| `semantics.py` | grounding, stable models, well-founded model | Lesson 5 |
| `semiring.py` | Kleene iteration over semirings | Lessons 6–7 |
| `incremental.py` | insertion propagation + DRed | Lesson 8 |
| `prolog.py` | unification + SLD resolution | Lesson 9 |
| `subsumption.py` | EL normalisation, compiled to Datalog | Lesson 10 |

## The core, in one pass (`datalog.py`)

**Terms are frozen dataclasses.** `Var`, `Const`, `Struct`, `Atom`,
`Literal`, `Rule` are all immutable and hashable. That one decision does
a lot of quiet work: rules can live in sets (magic.py dedupes its output
that way), tuples of constants can key dictionaries, and nothing ever
mutates behind your back.

**The tokenizer is a single regex** of named alternatives — whichever
group matched *is* the token kind. The parser is textbook recursive
descent, one method per grammar rule; the whole grammar is seven lines
in `_Parser`'s docstring.

**Safety is range restriction** (`validate`): every head variable and
every variable under `not` must be bound by a positive body literal.
This is what keeps every relation finite. The same function enforces the
function-symbol ban — the Datalog boundary from Lesson 9 is four lines
of `isinstance(a, Struct)`.

**Stratification is a graph problem.** Build predicate dependency edges,
find strongly connected components (Tarjan's algorithm, iterative so
Python's recursion limit never bites), and reject any negative edge
inside a component — that *is* "negation in a recursive cycle", and the
error message reconstructs the offending cycle by BFS. Stratum numbers
then fall out by relaxation: strictly above what you negate, at least as
high as what you use.

**The database is a dict of sets of tuples.** No storage engine, no
indexes: `rels["path"] == {("a","b"), ("a","c")}`. Matching an atom
against a tuple (`_match`) is one-way unification: variables take values
or must agree with earlier bindings. A rule body is evaluated by folding
`_match` over its literals under one growing substitution — which is
exactly a relational join, done as nested loops.

**Semi-naive is fifteen lines** (`Engine._eval_stratum`). Round one
evaluates every rule against the full database. After that, each
recursive rule is re-evaluated once per recursive body position, with
that position restricted to the previous round's *delta* and every other
position reading the full (already-updated) relations. Why is that
complete? Any new derivation must use at least one new fact — put the
delta there; and because "full" already contains the delta,
delta-x-delta derivations are covered too (the non-linear `path` rule in
the tests exists precisely to catch engines that get this wrong).
Duplicates cost nothing: sets absorb them.

## The satellites

**`magic.py` is a program-to-program function.** No evaluator changes at
all: it takes `Rule` objects in and returns different `Rule` objects
out, then hands them to the ordinary `Engine`. Read it as a compiler
pass — adornments are computed by simulating exactly the left-to-right
binding flow the evaluator itself uses.

**`semantics.py` is three short functions** once you see the shape:
`ground_program` instantiates rules over an envelope (the least model
with all negations granted — provably a superset of every stable model,
which is what makes exhaustive search sound), `_gamma` is the
Gelfond–Lifschitz operator (delete rules whose negated atoms are in the
candidate; forward-chain the rest), and both semantics are one-liners
over it: stable = "Γ(M) == M", well-founded = the least fixpoint of Γ∘Γ
with the undefined zone read off the gap.

**`semiring.py` deliberately regresses to naive evaluation.** Kleene
iteration recomputes every value each round, because semi-naive needs to
*subtract* what's already known and semirings don't have subtraction.
That absence is not a bug in the module; it is the observation that
leads to DBSP (Lesson 8's closing note).

**`incremental.py` reuses the engine's own delta machinery** in both
directions: insertion is `_eval_rule(delta_occ=...)` pointed at new
facts; DRed's over-delete phase is the same call pointed at *dying*
facts. One mechanism, three algorithms.

**`prolog.py` upgrades `_match` to real unification** — both sides may
contain variables, so bindings need chasing (`_walk`) and the occurs
check. SLD resolution is a recursive generator: `yield` is
"solution found", falling out of the loop is backtracking. Compare its
~60 lines of search with the engine's fixpoint loop: that contrast is
the whole top-down/bottom-up debate in code.

**`subsumption.py` is a compiler in the other direction.** Where
magic.py rewrites Datalog to Datalog, this one translates a *different
logic* (EL concept definitions) into Datalog: normalisation mints fresh
names for nested expressions, and the entire reasoning calculus becomes
five ordinary rules. When a problem's inference rules are monotone, "compile
it to Datalog" is a general-purpose trick — worth remembering.

## Honest limits, and where the real engines differ

Joins are nested loops with no indexes (Soufflé compiles to indexed
C++ joins; industrial engines use worst-case-optimal joins). Stable
models are found by exhaustive search over the candidate envelope
(clingo uses conflict-driven learning). Everything is batch (Feldera
maintains incrementally). Each simplification was chosen so the
algorithm's *idea* fits on one screen.

## Is this real, or just academic?

The gap between this code and a production engine is engineering, not
concept: Soufflé compiles the same semi-naive loop to parallel C++ with
indexed joins; RDFox does it in memory-optimised C++ with incremental
maintenance; RelationalAI adds worst-case-optimal joins. Reading this
repository is a legitimate on-ramp to those codebases — the loop you can
hold in your head here is the loop you will find there, industrialised.
Engine internals of this kind are a real, if specialised, employment
market: database kernels, static-analysis platforms, and knowledge-graph
vendors all hire for exactly this understanding.

## Exercises

1. Add a `--naive` flag to `Engine` that skips the delta discipline, and
   print per-round derived-fact counts for both modes on
   `programs/02-reachability.dl`. How do the counts differ, and why is
   the final result identical?
2. Add a comparison built-in (`X != Y`) to rule bodies: parser, safety
   rule (both operands must be bound — why?), and evaluation. Note how
   Lesson 1's `sibling` bug becomes fixable.
3. Add `max_rounds` protection to `Engine` and construct a program that
   would need it if function symbols were allowed. What stops you? (That
   is the point.)
4. Read `magic.py` end to end and hand-simulate the rewriting of
   `programs/01-family.dl` for `ancestor(bob, X)`. Check yourself
   against `--magic --trace`.
