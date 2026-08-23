# Assignment: build your own Datalog

Implement a Datalog interpreter from scratch, in any language, using
this repository as the reference implementation and grading oracle.
(Format modelled on Kris Micinski's CIS 700 project; weights included so
instructors can adopt it directly.)

## The language you must accept

Facts and rules in this repository's syntax (see
`lessons/getting-started.md`): lowercase constants, uppercase variables,
`head(X) :- body(X, Y), other(Y).`, `%` comments. You may ignore
weights (`@`), retraction (`~`), aggregation, and negation — until the
advanced milestone.

## Milestones and weights

| Milestone | Weight | What it means |
|---|---|---|
| 1. Parsing | 40% | Read a `.dl` file into facts and rules; reject malformed input with a useful message; enforce the safety rule (every head variable appears in a positive body literal). |
| 2. Naive evaluation | 50% | Compute the fixpoint: apply every rule to the known facts, add what's new, repeat until nothing changes. Any strategy is fine — correctness is what's graded. |
| 3. One advanced feature | 10% | Your choice of: semi-naive evaluation (show per-round delta counts), stratified negation (with a clear error on negation-in-a-cycle), or magic sets for one bound query. |

## Grading: differential testing

Your interpreter is graded by agreement with this repository:

1. **Fixed cases.** Every directory under `cases/` is a test: run
   `program.dl`, answer each query in `queries`, compare with
   `expected` (sorted, exact). Add `python3 tests.py` to see the
   reference implementation grade itself the same way.
2. **Generated cases.** `python3 benchmarks/generate.py chain 50` (and
   `tree`, `grid`) produce programs; your `path` relation must equal
   `python3 datalog.py -q 'path(X, Y)' <file>`'s answers.
3. **Your own case.** Contribute one new `cases/` directory that your
   implementation passes — ideally one that found a bug in it.

## Suggested extensions ladder (beyond the assignment)

Aggregation (`sum`/`count`/`min`/`max` heads), `--explain` derivation
trees, tabled top-down evaluation, DRed deletion — each has a reference
implementation and a lesson in this repository. Reading the reference
*after* writing your own is where most of the learning hides.
