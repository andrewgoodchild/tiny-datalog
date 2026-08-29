# Lesson 13 — Tabling: top-down without the cliff

The course has answered queries three ways, each with a flaw it owns
honestly: bottom-up (Lesson 2) computes everything whether you asked or
not; magic sets (Lesson 6) fixes that by rewriting the program before
running bottom-up; SLD (Lesson 10) is natively goal-directed but repeats
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
implements the iterative QSQR formulation — about a hundred lines, and
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

What this module leaves out — negation. Tabling under negation is SLG
resolution, which computes the well-founded semantics of Lesson 5;
building it is how XSB earned its place in the history told in
Lesson 0.


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

That closes the evaluation arc: four strategies, one semantics, and
every pair of them checkable against each other by the conformance
suite in `tests.py`. The remaining lessons step outside evaluation —
[14](14-containment.md) asks what a query means on *every* database,
[15](15-writing-rules.md) is about authoring rules rather than
running them, and [16](16-category-theory.md) names the mathematics.

Next: [containment](14-containment.md). The last lesson asks a
question evaluation never does: what does this query compute on
*every* database?
