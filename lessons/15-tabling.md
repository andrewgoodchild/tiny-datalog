# Lesson 15 — Tabling: top-down without the cliff

The course has answered queries three ways, each with a flaw it owns
honestly: bottom-up (Lesson 2) computes everything whether you asked or
not; magic sets (Lesson 7) fixes that by rewriting the program before
running bottom-up; SLD (Lesson 11) is natively goal-directed but repeats
subgoals endlessly and falls off a cliff on left recursion. Tabling is
the fourth strategy — top-down, goal-directed, and it terminates.

## The cliff, first

`programs/left-recursive.dl` defines ancestor the way a database
person naturally would:

```prolog
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Z) :- ancestor(X, Y), parent(Y, Z).   % left recursion
```

Bottom-up doesn't care. But ask prolog.py and SLD expands `ancestor`
into `ancestor` into `ancestor` — before ever consuming a fact — and
only the depth bound saves it (the answers arrive flagged "search
truncated"). This isn't a quirk; it's the reason Prolog programmers
memorise rule-ordering folklore.

The tabling idea, in one sentence: when a subgoal calls a *variant of
itself*, don't descend — that way lies the loop — instead read whatever
answers that subgoal's table already has, and arrange to come back for
the ones that haven't arrived yet. Production engines (XSB's SLG,
SWI-Prolog's tabling) do the "come back" by *suspending* the looping
call and *resuming* it each time its table gains an answer. This
implementation does something simpler with the same meaning: re-run
every query to fixpoint until no table grows — more recomputation,
much less machinery, identical tables (exercise 2 measures the
difference).

## The fix: give every subgoal a table

```sh
$ python3 tabling.py programs/left-recursive.dl -q 'ancestor(abe, X)' -t
?- ancestor(abe, X)   [tabled]
   ancestor(abe, ann).
   ancestor(abe, bob).
   ancestor(abe, carl).
   ancestor(abe, dee).
   (4 answers; 6 subgoal tables, 11 rounds)
   table ancestor(abe, _): 4 answers
   table parent(abe, _): 2 answers
   ...
```

A **subgoal** is a predicate plus a pattern of bound arguments —
`ancestor(abe, _)`, and each subgoal gets a **table** of answers,
computed once and shared by every occurrence. The recursive call inside
`ancestor`'s own rule doesn't descend; it *reads the table*, and an
outer fixpoint loop grows all tables until nothing changes (`tabling.py`
implements the iterative QSQR formulation — under two hundred lines, and
lesson-sized on purpose; production SLG engines like XSB do the same
with suspension and resumption instead of re-iteration).

Termination is the usual Datalog gift twice over: finitely many
subgoals, finitely many answers per table.

## The punchline: you have seen these tables before

Run the bound reachability query both ways:

```sh
python3 tabling.py programs/reachability.dl -q 'path(n5, X)' -t
python3 datalog.py --magic --trace -q 'path(n5, X)' programs/reachability.dl
```

The tabling run creates path tables for exactly {n5, n6, n7, n8} — and
the magic run's `magic#path#bf` relation contains exactly {n5, n6, n7,
n8}. Same sets, provably doing the same job: **magic sets is tabling
performed at compile time; tabling is magic sets performed at run
time.** One is a program transformation, the other a smarter
interpreter, and the demand they compute is identical. That equivalence
(the Query-Subquery/magic-sets duality) is one of the field's quietly
beautiful
theorems, and you can now verify it with two shell commands.

## Negation: finish the table first

Tabling and negation meet at one question. To answer `not q(a)`, you
need q's table to be *complete*, holding every answer it will ever
hold. A half-grown table could wrongly say "absent" about something
that arrives two rounds later. That is Lesson 3's ordering problem
again, met top-down.

For stratified programs the answer is the one Lesson 3 gave. A negated
subgoal belongs to a lower stratum, so nothing in its table can depend
on the rule asking about it. `tabling.py` therefore pauses on `not q(a)`,
grows every table of q's stratum and below to fixpoint, marks them
complete, and only then looks:

```
$ python3 tabling.py programs/tweety.dl -q 'flies(X)' -t
?- flies(X)   [tabled]
   flies(tweety).
   (1 answer; 6 subgoal tables, 4 rounds)
   table abnormal(opus): 1 answer
   table abnormal(tweety): 0 answers
   table bird(_): 2 answers
   table flies(_): 1 answer
   table penguin(opus): 1 answer
   table penguin(tweety): 0 answers
```

The tables show demand at work. `not abnormal(X)` was asked about
Tweety and Opus only, so `abnormal` got one table per bird, each
completed before it was read. `abnormal(tweety)` is complete and
empty, and that is what lets Tweety fly. pyDatalog makes the same
simplification, and the differential fuzzer in `tests.py` holds this
module to the bottom-up engine's answers on random programs with
negation.

## A search problem: eight queens

Place eight queens on a chessboard so that no two attack each other.
pyDatalog's tutorial solves it with arithmetic, `X1 != X2+N`. This
engine has none (Lesson 14), so the board goes in as facts instead:
`attacks(R1, D, R2)` says that queens D columns apart, in rows R1 and
R2, attack each other. Compatibility is then a stratified negation,
exactly the kind the previous section made possible:

```prolog
% programs/queens.dl  (python3 benchmarks/generate.py queens 8)
ok(R1, D, R2) :- row(R1), row(R2), dist(D), not attacks(R1, D, R2).

queens1(X0) :- row(X0).
queens2(X0, X1) :- queens1(X0), next2(X0, X1).
queens3(X0, X1, X2) :- queens2(X0, X1), next3(X0, X1, X2).
...
next2(X0, X1) :- queens1(X1), ok(X0, d1, X1).
next3(X0, X1, X2) :- next2(X1, X2), ok(X0, d2, X2).
...
```

`queensK` is a set of compatible queens in the first K columns.
`nextK` checks only that the *last* queen is compatible with each
earlier one, and leans on `queensK` to have checked the rest. The
structure is pyDatalog's, and so is the trick: it only works because
someone asks `nextK` about boards that are already valid.

```
$ python3 tabling.py programs/queens.dl -q 'queens8(r0, X1, X2, X3, X4, X5, X6, X7)'
?- queens8(r0, X1, X2, X3, X4, X5, X6, X7)   [tabled]
   queens8(r0, r4, r7, r5, r2, r6, r1, r3).
   queens8(r0, r5, r7, r2, r6, r3, r1, r4).
   queens8(r0, r6, r3, r5, r7, r1, r4, r2).
   queens8(r0, r6, r4, r7, r1, r3, r5, r2).
   (4 answers; 1220 subgoal tables, 92 rounds)
```

Four solutions start with a queen in row 0. Unpin the first queen and
you get all 92. Now ask the same question three ways:

| Strategy | All 92 solutions | Why |
|---|---|---|
| tabling | 0.4s, 2,844 tables | `nextK` is only asked about valid partial boards |
| magic sets | 1.9s | the same demand, compiled into the program |
| bottom-up | did not finish in 10 minutes | must build all of `nextK` first |

The bottom-up row is the instructive one. Read on its own, `next8`
says only that the eighth queen is compatible with each of the seven
before it, whose own placement is unconstrained. That relation is
huge: the `nextK` relations hold 2,527,544 facts for an 8×8 board,
against 7,414 for 6×6 (0.3s bottom-up) and 126,504 for 7×7 (12.5s).
Bottom-up computes every one of them, because nothing tells it which
boards matter. Tabling and magic sets carry that information down
from the query. No other example in the course shows the gap between
"compute everything" and "compute what was asked" this sharply.

It also shows the fence. Datalog has no lists, so the rules are
unrolled one column at a time and each board size is its own program.
That is why the file is generated. A single program for any N needs
compound terms, which take you over Lesson 11's boundary into
`prolog.py` (no termination guarantee). Alternatively it needs answer
set programming's *choice rules*, which turn search into a model to
be found (Lesson 5's territory: clingo solves N-queens in a handful
of lines). Datalog can describe one board. Describing a family of
boards needs a more expressive language than Datalog.

## What full SLG adds

Negation *through* recursion is where the simple rule breaks:

```
$ python3 tabling.py programs/win.dl -q 'win(X)'
error: program is not stratifiable — negation occurs inside a recursive cycle: win --not--> win.  No stratum assignment exists, so the program has no stratified model.  Tabling under unstratified negation is full SLG resolution, which computes the well-founded semantics (Lesson 15); datalog.py --models computes it bottom-up.
```

To know whether `win(a)` holds, you need `win(b)` finished first, and
to finish `win(b)` you need `win(a)`. No table can be completed before
the other. **SLG resolution** (Chen & Warren 1996), the engine inside
XSB Prolog, answers such programs with three ideas this module does
without:

1. **Suspend and resume.** When a call meets a variant of itself, SLG
   does not re-run everything in rounds. It *suspends* the consumer
   and *resumes* it each time the producer's table gains an answer.
   No work is repeated, which is the difference exercise 2 below
   measures. Tamaki and Sato's OLDT resolution (1986) introduced this
   for positive programs.
2. **Detect completion.** SLG tracks which calls depend on which, and
   declares a whole group of mutually dependent tables complete the
   moment none of them can grow. That is a strongly connected
   component check, run during evaluation, and it is what licenses
   negation without strata.
3. **Delay, then simplify.** When a negative literal depends on a
   table that cannot complete first, as `win` does, SLG *delays* it:
   it records the answer as conditional on the delayed literal and
   carries on. Later, when the delayed literal is resolved, the
   condition is *simplified* away, or the answer is dropped. Answers
   whose conditions never resolve are reported as *undefined*.

Those undefined answers are exactly the well-founded model of Lesson 5,
computed top-down and only for what the query needs. On `win.dl`, SLG
would report `win(a)` and `win(b)` as undefined, matching what the
bottom-up route says:

```
$ python3 datalog.py --models programs/win.dl
Well-founded model (three-valued):
  true:      (EDB facts only)
  undefined: win(a).  win(b).
```

The extra precision has a price. Each of the three ideas needs
bookkeeping that iterative QSQR avoids: consumer continuations,
dependency stacks, and conditional answers. Together they make up
several hundred lines of the hardest code in any tabling engine. This
course already computes the well-founded model bottom-up
(`semantics.py`, Lesson 5), so SLG here would teach the same semantics
a second time at a high cost in readability. It is the right design for
a Prolog system that must run arbitrary programs top-down. For a course
that wants every module readable in a sitting, stratified negation is
the stopping point.


## The other reason top-down survives: debugging

Goal-direction is only half of why the literature keeps building
top-down evaluators. The other half is that **a bottom-up trace
follows the data, not the program**: Lesson 2's `--trace` shows deltas
arriving in rounds, and `--explain` reconstructs a derivation after
the fact, but neither lets you *step through a rule* the way you step
through a function — watch this subgoal being tried, see that binding
fail, continue. Interactive Datalog debuggers in the research
literature are built on top-down semantics for exactly that reason:
stepping is native there. This module is the doorway — a tabled
top-down evaluator with the same semantics as the engine — and
turning it into a stepper is an exercise in attaching a prompt to
`_prove`.

## Under the hood: memoisation applied to resolution

**`tabling.py` is memoisation applied to resolution.** A dictionary
from call patterns to answer sets, a prover that reads tables instead
of descending, and an outer loop that re-runs everything until no table
grows. Compare its `_pattern` function with magic.py's adornments —
same idea, computed at run time instead of compile time.

## Exercises

1. Compare `tabling.py -t` and `--magic --trace` on
   `ancestor(bob, X)` over `programs/family.dl`. Match each table to
   a magic fact.
2. The rounds count for the left-recursive query is larger than the
   answer count. Why does iterative QSQR pay extra rounds, and what do
   real SLG engines do instead? (One sentence each.)
3. Add a second bound query to the same engine object. Why do the
   tables reset, and what would it take to share them across queries
   (the real systems' "table space")?
4. Write a program + query where tabling creates *fewer* tables than
   magic sets creates magic facts, or argue from the construction that
   it can't happen.
5. Generate the puzzle for N = 2 through 6 with
   `python3 benchmarks/generate.py queens N`, and predict before you
   run it: for which N are there no solutions at all? Then swap the
   order of the two literals in the `queensK` rules, so `nextK` comes
   first. What happens to the table count, and why?

That closes the evaluation arc: four strategies, one semantics, and
every pair of them checkable against each other by the conformance
suite in `tests.py`. The remaining lessons step outside evaluation —
[16](16-containment.md) asks what a query means on *every* database,
[17](17-writing-rules.md) is about authoring rules rather than
running them, and [19](19-neighbours.md) compares the neighbours and
names the mathematics.

Next: [containment](16-containment.md). The last lesson asks a
question evaluation never does: what does this query compute on
*every* database?
