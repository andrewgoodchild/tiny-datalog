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
you get all 92. Now ask the same question four ways:

| Strategy | All 92 solutions | Why |
|---|---|---|
| tabling | 0.4s, 2,844 tables | `nextK` is only asked about valid partial boards |
| SLG (`slg.py`, below) | 0.07s, 2,844 tables | the same tables, and no table re-solved |
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
error: program is not stratifiable — negation occurs inside a recursive cycle: win --not--> win.  No stratum assignment exists, so the program has no stratified model.  Tabling under unstratified negation is full SLG resolution, which computes the well-founded semantics (Lesson 15); slg.py runs it top-down, datalog.py --models bottom-up.
```

To know whether `win(a)` holds, you need `win(b)` finished first, and
to finish `win(b)` you need `win(a)`. No table can be completed before
the other. **SLG resolution** (Chen & Warren 1996), the engine inside
XSB Prolog, answers such programs with three ideas that `tabling.py`
does without and `slg.py` implements:

1. **Suspend and resume.** When a call meets a subgoal that already
   has a table, SLG does not re-run anything in rounds. The call
   becomes a *consumer*: the rest of its rule body, parked on that
   table. Each answer the table gains is pushed to each consumer
   exactly once. Tamaki and Sato's OLDT resolution (1986) introduced
   this for positive programs. Python cannot pause a function and
   resume it twice, so `slg.py` stores a parked call as plain data:
   the calling subgoal, the rule head, the body literals still to
   prove, and the substitution so far.
2. **Detect completion.** When no work is left, the incomplete tables
   and the calls between them form a graph. A strongly connected
   component with no call out to another incomplete table can never
   grow again, so the whole component is complete. It is what lets
   `not q(a)` be decided without strata: wait until q(a)'s component
   completes, then look. Finding components is Tarjan's algorithm
   again, the one `stratify` uses, but running it over every table
   each time the work runs out costs time quadratic in the number of
   tables. `slg.py` does what XSB does instead, below.
3. **Delay, then simplify.** A component can be stuck: every call
   still waiting inside it is a `not` on a table in the same
   component, and each waits for the others, as `win` does. SLG
   *delays* those literals. It carries on as if they had succeeded and
   records them on the answer as a *condition*. Once the component
   completes, conditions are *simplified* against the finished tables:
   a literal now known true is struck out, a literal known false
   kills its condition, and an answer whose condition empties is true.
   Answers whose conditions never resolve are reported as *undefined*.

Those undefined answers are exactly the well-founded model of Lesson 5,
computed top-down and only for what the query needs:

```
$ python3 slg.py programs/win.dl -q 'win(X)'
?- win(X)   [SLG]
   win(a).   undefined: if not win(b)
   win(b).   undefined: if not win(a)
   (0 true, 2 undefined; 6 subgoal tables, 2 completions, 2 delays)
```

The bottom-up route agrees:

```
$ python3 datalog.py --models programs/win.dl
Well-founded model (three-valued):
  true:      (EDB facts only)
  undefined: win(a).  win(b).
```

The leftover condition is the explanation: `win(a)` is undefined
because it hangs on `not win(b)`, which hangs on `not win(a)`. Lesson
5's café paradox reads the same way. Carol's answer is settled and
Bob's is named, along with the one literal his answer turns on:

```
$ python3 slg.py programs/cafe-paradox.dl -q 'eats_in_cafe(X)'
?- eats_in_cafe(X)   [SLG]
   eats_in_cafe(carol).
   eats_in_cafe(bob).   undefined: if not household_cooks(cafe_house)
   (1 true, 1 undefined; 23 subgoal tables, 4 completions, 2 delays)
```

### The fourth idea nobody mentions: answer completion

Simplification alone is not enough. Delaying lets answers be derived
from conditional answers, and an answer can end up resting on
nothing but itself:

```prolog
p(a, a).
s1(Y) :- p(Y, a), not s2(Y, Y).
s1(d) :- s1(X), not s1(X).
s2(X, X) :- s1(Y), t1(X, Y), X != X, not s2(X, Y).
```

While `not s2(a, a)` is delayed, `s1(a)` is conditional. The second
rule derives `s1(d)` from it, and then derives `s1(d)` again from
`s1(d)` itself. When the component completes, `s2(a, a)` has no
answers, so `s1(a)` is true and the first route to `s1(d)` dies (it
needed `not s1(a)`). The second route survives simplification: its
condition is `s1(d)` and `not s1(d)`, both still undecided. But `s1(d)`
is holding itself up, with nothing outside the loop supporting it.
That is an *unfounded set* in the well-founded semantics' own
definition, and it is false, not undefined. `slg.py`'s
`_drop_unfounded` finds such answers: everything not reachable from
answers with outside support is dropped, and simplification runs
again. Chen and Warren call this step answer completion.

This program was not written by hand. The test suite's fuzzer, which
holds `slg.py` to `semantics.py`'s well-founded model on random
unstratified programs, found it when answer completion was switched
off. That is how this module earns its claim. Every answer, true or
undefined, matches the bottom-up computation of the same semantics.

### Completion without Tarjan: the completion stack

A first version of `slg.py` reran Tarjan's algorithm over every
incomplete table whenever its work ran out. On all 92 eight-queens
solutions that took 1.6 seconds, 97% of it spent finding components.
Three economies, all standard in XSB, brought the query to 0.04
seconds (0.07 for the whole command, start-up included):

- **A completion stack.** Tables go on a stack as they are created,
  newest on top. When the work runs out, scan down from the top,
  tracking the oldest incomplete table called so far. The first table
  reached that is no younger than that oldest call marks a segment that
  calls nothing below itself, so it can be completed whole. The scan
  only touches tables that are about to complete. The segment may hold
  several components at once, so XSB calls it an *approximate SCC*.
  That is safe: no table in it can grow.
- **Tarjan only when it buys precision.** Completing a segment whole
  is blunt in one case: when it is stuck on a `not` inside itself.
  Delaying everything in it would be sound, but a `not` that the
  completion of one smaller component would decide should be decided,
  not delayed. Only then does Tarjan run, on that segment alone.
- **Facts complete at once.** A predicate defined only by facts calls
  nothing, so its table is complete the moment it is filled, and a
  `not` on it never waits. Without this, a fact table made while a
  large segment was open sat buried in the stack, and every `not` on
  it looked stuck. In eight queens that is every `not attacks(...)`.

A fourth, *local scheduling*, came later. The first version had a
single work queue for the whole query, so a segment was only examined
once *all* the work had run out. XSB keeps work per table and runs the
newest table's first, and so does `slg.py` now. When the top of the
stack runs out of work, it is checked straight away, before any older
table runs again, and completed if it calls nothing below it. On all 92
solutions, the global queue completed 54 large groups. Local
scheduling completes 2,400, one for every table that is not just
facts:

```
$ python3 slg.py programs/queens.dl -q 'queens8(X0, X1, X2, X3, X4, X5, X6, X7)'
...
   (92 true, 0 undefined; 2844 subgoal tables, 2400 completions, 0 delays)
```

The time is the same, and the answers are too. What changes is when a
table is finished. A finished table frees its consumers and its call
edges, a `not` on it is decided instead of parked, and, as the next
section shows, a finished table can answer other calls.

### Subsumptive tabling

Every engine so far starts a table for each new *variant* of a call:
`path(n1, n5)` gets its own table even when `path(X, Y)` holds the
answer. *Subsumptive* tabling answers a call from a table whose
pattern is more general, filtering it, and starts no new table.
`programs/from-start.dl` is built to need it: it fills `path(X, Y)`
over a 60-node chain, then asks `path(n1, Y)` for each Y, every call
ground:

```
$ python3 slg.py programs/from-start.dl -q 'from_start(Y)'
...
   (59 true, 0 undefined; 7202 subgoal tables, 3601 completions, 0 delays)
$ python3 slg.py programs/from-start.dl -q 'from_start(Y)' -s
...
   (59 true, 0 undefined; 3 subgoal tables, 2 completions, 0 delays, 1829 subsumed calls)
```

Variant tabling makes 7,202 tables, because each ground `path(n1, nK)`
calls `path(n2, nK)`, and so on down the chain. With `-s` there are
three, `from_start(Y)`, `path(X, Y)` and `edge(X, Y)`, and the query
runs about fourteen times faster (Python's start-up aside).

The general table can serve a call while it is still growing. Inside
`path(X, Y)`'s own rule, `path(X, Z) :- edge(X, Y), path(Y, Z)` calls
`path(n2, Z)`, `path(n3, Z)` and so on, and each of those calls is
served by `path(X, Y)` itself. The call becomes one of its consumers,
the way a recursive call does, and the completion stack sees it as a
dependency, so they complete together. Two lookups keep this cheap:

* **Finding the general table.** The tables of each predicate are
  grouped by which arguments their patterns leave free, so a call
  checks one candidate per group instead of every table.
* **Reading only its slice.** A served call never scans the general
  table. It reads an index on the positions it binds (`_slice`),
  built the first time those positions are asked for. While the
  table grows, the index grows with it, and each waiting call is
  filed under its own slice, so a new answer goes only to the calls
  it matches. XSB's answer tries do this for every pattern.

Without the slices, every waiting call received every new answer of
`path(X, Y)` and threw most of them away: `-s` built 3 tables and
still ran slower than the 62 it built when it could read only
complete ones. The first lookup matters on eight queens. When each
call scanned the queens predicates' tables, hundreds of them, `-s`
was 2.7 times slower, though it saved only 8 tables of 2,844. Grouped,
it breaks even (52 ms against 50). It is still opt-in, because a
program with nothing to share pays for the lookups and gets nothing
back. (`tabling.py` has no `-s`: it re-solves every table each round,
and serving a call from a table that is re-solved anyway saves
nothing.)

### Aggregation, tabled

Both tabled engines now accept aggregates, which they used to refuse.
The front end they share (`split_aggregates` in `tabling.py`) gives
each aggregate rule's body a table of its own, holding one answer per
distinct body solution, which is the set Lesson 13 folds. The
aggregate then waits for that table to complete, the way `not` does,
and folds it once:

```
$ python3 slg.py programs/spending.dl -q 'total(P, T)'
?- total(P, T)   [SLG]
   total(alice, 180).
   total(bob, 990).
   (2 true, 0 undefined; 3 subgoal tables, 2 completions, 0 delays)
```

The two refusals left are principled. A cycle through an aggregate
has no stratified answer, so both engines refuse it, and `slg.py`,
which runs unstratified programs, refuses to fold answers that are
undefined, for the reason `semantics.py` gives: what an aggregate over
undefined facts should mean is still debated.

Conditions are kept minimal too. An answer true under condition A
needs no second condition "A and B", so that one is absorbed.

### The table space, and constraints as queries

When a query returns, every table it made is complete, and the
program cannot change under the engine. So the tables can stay,
ready for the next query to read. Real systems call this collection
the **table space**. Both engines keep one:

```
$ python3 slg.py programs/reachability.dl -q 'path(n5, X)' -q 'path(n3, X)' -q 'path(n5, X)'
...
   (3 true, 0 undefined; 8 subgoal tables, 4 completions, 0 delays)
...
   (7 true, 0 undefined; 16 subgoal tables, 8 completions, 0 delays)
...
   (3 true, 0 undefined; 16 subgoal tables, 8 completions, 0 delays)
```

The counts are for the whole table space. The second query adds 8
tables, because `path(n3, X)` reaches `path(n5, X)` and reads its
finished table instead of building another. The third query adds
nothing and does no work. An error halfway through a query (a `sum`
over a name, say) empties the table space, because its tables are no
longer known to be complete. The one thing that would make a kept
table wrong is a change to the facts, which is the next section.

A kept table also answers a question the engines used to refuse: is
an integrity constraint (Lesson 17) violated? A constraint `:- body.`
is a query whose every answer is a counterexample. `constraint_goals`
in `tabling.py` gives each one a rule, `#constraint1(P) :- body.`,
whose head holds every variable the body binds. Nothing calls that
predicate, so no other answer changes, and checking the constraint is
one more query. It reads the tables the real queries left behind:

```
$ python3 slg.py programs/lending-draft2-checked.dl -q 'may_borrow(P)'
...
constraint violated: :- may_borrow(P), suspended(P).
   may_borrow(kim), suspended(kim)
   (1 counterexample)
```

Magic sets does the same, with one rewriting per constraint. So now
every engine reports the counterexamples the base engine reports,
with the same exit status 3, and the conformance tests check that.
`slg.py` has a third verdict for an unstratified program: a
constraint whose body is only *undefined* is neither violated nor
satisfied, and the CLI says so (`constraint undefined: ...`).

### Incremental tabling

Lesson 10 kept a materialisation up to date as facts changed. The
tabled engines can do the same for their table space, and the
mechanism is shorter, because a table records who asked for it. Every
call is an edge from the calling table to the called one, and both
engines keep those edges (`callers`). `apply(script)` takes facts to
insert and `fact~.` ones to retract, as `incremental.py` does. It
finds each table whose pattern matches a changed fact, then walks the
edges back up to every table that read one of those, directly or not.
Only those tables can see the change. The rest are untouched, and
still right.

The reached tables are rebuilt from empty, callee before caller, one
strongly connected group at a time (Tarjan's algorithm, which Lesson
3 used to stratify, gives that order). Before rebuilding a group,
`apply` looks at what it reads. If nothing it reads came out
different, the group is put back as it was, unrebuilt. So the walk
stops at the first table an update leaves unchanged. `-u` does this
between queries on the command line:

```
$ python3 slg.py programs/reachability.dl -q 'path(n1, X)' -u 'edge(n8, n9).' -q 'path(n1, X)'
...
   (9 true, 0 undefined; 20 subgoal tables, 10 completions, 0 delays)
% update edge(n8, n9).   (7 tables rebuilt, 2 unchanged, 11 untouched)
...
   (9 true, 0 undefined; 20 subgoal tables, 16 completions, 0 delays)
```

The new edge changes `edge(n8, Y)`, and with it `path(n8, X)` up to
`path(n4, X)`, which all gain `n9` and `n10`. `path(n3, X)` is rebuilt
too, because it reads `path(n4, X)`, but it comes out the same: it
already reached `n9` and `n10` through `edge(n3, n9)`. So
`path(n2, X)` and `path(n1, X)` are put back without a rebuild, and
the second query does no work at all. The rebuilding happens inside
`apply`, which is why the completions go up before the query asks.

Rebuilding a table from empty is blunter than Lesson 10's counting
and DRed, but it needs no special case for negation. A new fact can
*remove* an answer from a table that negates it: insert `q(a)` under
`p(X) :- r(X), not q(X)` and `p(a)` goes. A method that only added
answers would miss that, which is why DRed deletes before it
re-derives. A rebuilt table starts empty, so it cannot keep a stale
answer. Two details keep it honest:

* Every reached table is set aside before any is rebuilt. A rebuild
  that newly calls one not yet settled (an update can create calls
  the old tables never made) builds it afresh instead of reading a
  stale copy.
* A whole group is rebuilt or put back together. Inside a recursive
  group, one table's old answers may rest on another's, so it is
  never safe to keep half.

The fuzzer checks the result: random programs, random updates, and a
fresh evaluation of the changed program to compare against, for both
engines, and under the well-founded semantics for `slg.py`. This is
the idea of XSB's incremental tabling, though XSB rebuilds a table
lazily, when a query next needs it, and these engines do it eagerly.

### What it costs, and why both modules stay

`slg.py` is about 630 lines to `tabling.py`'s 560, and it borrows
that module's front end: the clause index, the call pattern, the head
match, the aggregate split and fold, and the table space. The two are
the modules allowed more than 500 lines: 700 for `slg.py`, 600 for
`tabling.py`. The extra lines are the bookkeeping iterative QSQR
avoids: parked consumers, the completion stack, conditions on
answers, and the simplification loop.
In exchange it never repeats work, and it accepts every function-free
program, stratified or not. The repeated work is what you feel. On a
300-node chain (`python3 benchmarks/generate.py chain 300`),
`path(n1, X)` takes `tabling.py` 32 seconds, in 1,196 rounds, and
`slg.py` 0.1 seconds.

`tabling.py` stays because it is the shorter path to the main idea.
A table per subgoal, read instead of re-derived, is the whole of
tabling, and its fixpoint loop shows that in one screen. `slg.py` is
the same idea with a scheduler. Read `tabling.py` first, then this
section, then `slg.py`. On stratified programs the two must agree, and
the tests check that their tables are the same sets.

SLG is also the fifth engine in `engines.py`, so
`datalog.py --engine slg -q ...` works, and the conformance suite and
the differential fuzzer run every stratified program through it. There
it refuses unstratified programs like the other four do: the engine
interface returns one set of answers, and only on stratified programs
is the undefined set guaranteed empty. For the three-valued answers,
run `slg.py` itself.

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

**`slg.py` replaces the outer loop with work queues, one per table.** `_step` proves
one literal of one frame. A positive call parks the frame in
`consumers` and catches it up on the table's answers so far, and
`_answer` pushes each new answer to every consumer. A negative call
parks in `waiting` until its table completes, and an aggregate parks
in `folds`. `_evaluate` always runs the newest table's work. When the
top of the stack has none left, it asks `_closed_segment` for a top
segment that can no longer grow and hands it to `_settle`, which
either completes it (`_complete`, then `_simplify`) or, if it is stuck
on a `not`, asks `_bottom_component` for its exact bottom component
and completes or delays that. Run any query with `-t` to see
the work counters: on the left-recursive ancestor query, 10 steps in
total, where `tabling.py` reports 11 rounds, each of which re-solves
every table. (`parent` is all facts, so its tables are filled when
called and add no steps.)

## Exercises

1. Compare `tabling.py -t` and `--magic --trace` on
   `ancestor(bob, X)` over `programs/family.dl`. Match each table to
   a magic fact.
2. The rounds count for the left-recursive query is larger than the
   answer count. Why does iterative QSQR pay extra rounds, and what do
   real SLG engines do instead? (One sentence each.) Then run the
   query under `slg.py -t` and say which of its work counters
   corresponds to a round's re-solving.
3. Run `path(n1, X)` on `programs/reachability.dl`, then
   `-u 'edge(n3, n9)~.'`. Before you run it, predict the three counts
   `apply` prints: rebuilt, unchanged, untouched. Then write an update
   to `r` and `q` under `p(X) :- r(X), not q(X).  t(X) :- p(X).` that
   rebuilds `p(X)` but leaves `t(X)` unchanged.
4. Write a program + query where tabling creates *fewer* tables than
   magic sets creates magic facts, or argue from the construction that
   it can't happen.
5. Generate the puzzle for N = 2 through 6 with
   `python3 benchmarks/generate.py queens N`, and predict before you
   run it: for which N are there no solutions at all? Then swap the
   order of the two literals in the `queensK` rules, so `nextK` comes
   first. What happens to the table count, and why?
6. Run `programs/from-start.dl` under `SLGEngine(clauses, True)` and
   look at `engine.indexes` and `engine.sliced` while it runs (break
   in `_answer`, or print from it). Which table has an index, which
   calls wait on its slices, and when do they stop waiting? Why does
   a ground call such as `path(n1, n5)` need no index once `path(X,
   Y)` is complete?

7. Write the smallest program you can on which `slg.py` reports an
   answer undefined *and* the answer has two conditions (the CLI
   joins them with "or if"). What does each condition say about how
   the answer could have been true?

That closes the evaluation arc: five strategies, one semantics, and
every pair of them checkable against each other by the conformance
suite in `tests.py`. The remaining lessons step outside evaluation —
[16](16-containment.md) asks what a query means on *every* database,
[17](17-writing-rules.md) is about authoring rules rather than
running them, and [19](19-neighbours.md) compares the neighbours and
names the mathematics.

Next: [containment](16-containment.md). The last lesson asks a
question evaluation never does: what does this query compute on
*every* database?
