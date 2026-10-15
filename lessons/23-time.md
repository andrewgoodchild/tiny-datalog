# Lesson 23 — Time: facts that stop being true

Every program so far has described a world that holds still. Alice
works at Acme, and that is that. Real records are not like that: Alice
works at Acme until the day she starts at Globex, and a payroll system
that pays her twice, or not at all, is wrong in a way that costs money.

There are two ways to make facts stop being true. One is to delete
them, and lesson 10 showed how an engine repairs its conclusions when
you do. The cost is history: once the old fact is gone, nobody can ask
where Alice worked in 2021. The other way deletes nothing. Every
statement is kept, with the date it took effect, and the rules work out
when each one was true. That is this lesson. It needs one thing the
engine did not have before, a way to order dates, so it starts there.
Lessons 3, 13 and 14 are the prerequisites.

## Comparisons, and why they are allowed

Lesson 14 explained why the engine has no `+`: a built-in that makes
new values can make a relation infinite, and termination goes with it.
A comparison is different. `D < T` makes nothing. It looks at two
values that already exist and says yes or no, so it can only *remove*
answers. That is why the engine now has six of them: `<`, `<=`, `>`,
`>=`, `=` and `!=`.

The price is lesson 14's mode discipline: both sides must already have
values. Leave one side unbound and the engine refuses, just as it does
for a variable under `not`:

```
$ python3 datalog.py programs/late-unsafe.dl
error: unsafe rule: variable T of comparison D < T is not bound by a positive literal in: late(L) :- due(L, D), D < T.
```

"Late compared with when?" Without `T`, the rule asks about every
possible date, and there is no such relation to compute. The fix is to
say what `T` is, with a fact like `today("2024-04-01")` and a literal
`today(T)` in the body. Where in the body you write the comparison
does not matter: the engine joins the positive literals first, then
applies comparisons, then negations.

Numbers compare as numbers and strings compare as text. ISO dates such
as `"2024-03-01"` are written biggest unit first with fixed widths, so
comparing them as text compares them as dates. That convention is the
whole reason this lesson can work with dates without a date type.
Ordering a number against a string (`3 < "abc"`) is an error rather
than a guess, while `=` and `!=` between them are simply false and
true.

## Valid time: statements, not states

`programs/employment.dl` records statements, each with the date it took
effect:

```prolog
said(alice, works_at, acme,    "2019-03-01").
said(alice, works_at, globex,  "2022-07-15").
said(alice, lives_in, leeds,   "2019-03-01").
said(alice, lives_in, york,    "2023-01-10").
said(bob,   works_at, acme,    "2020-05-01").
said(bob,   works_at, initech, "2021-09-01").
said(carol, works_at, globex,  "2021-01-04").
said(alice, knows,    bob,     "2020-02-11").   % not functional: accumulates

functional(works_at).      % one employer at a time
functional(lives_in).      % one home at a time
```

A **functional** relation has one value at a time, so a later statement
about the same subject ends the earlier one. Knowing Bob does not stop
when Alice meets Carol, so `knows` is not functional, and its
statements pile up. The rules say this directly:

```prolog
superseded(E, R, O, F, U) :- said(E, R, O, F), functional(R),
                             said(E, R, O2, U), O != O2, F < U.
ends(E, R, O, F, min(U)) :- superseded(E, R, O, F, U).
```

A statement is superseded by any later one with a different value, and
it ends at the *first* of those, which is lesson 13's `min`. From there
each statement gets a validity interval, `[From, Until)`, half-open so
that the day Alice joins Globex is a Globex day and not an Acme one:

```prolog
until(E, R, O, F, U) :- ends(E, R, O, F, U).
until(E, R, O, F, "9999-12-31") :- said(E, R, O, F), not ended(E, R, O, F).
ended(E, R, O, F) :- ends(E, R, O, F, _).

holds_at(E, R, O, T) :- until(E, R, O, F, U), asked(T), F <= T, T < U.
```

A statement that nothing has superseded is still true, and its
interval needs an end anyway. `"9999-12-31"` is a **sentinel**, a value
that means "no end yet". That is a convention, not logic, and SQL
databases use the same one. `asked/1` lists the moments we want to ask
about (`"2021-06-30"` and `"2024-01-01"`):

```
$ python3 datalog.py -q 'holds_at(alice, works_at, O, T)' programs/employment.dl
?- holds_at(alice, works_at, O, T)
   holds_at(alice, works_at, acme, "2021-06-30").
   holds_at(alice, works_at, globex, "2024-01-01").
   (2 answers)
```

Nothing was deleted to get the second answer. The Acme statement is
still in the file and still true *of 2021*. The Globex statement did
not overwrite it, it bounded it. That is the difference between a
record of statements and a record of states, and it is how event
sourcing works: keep the events, derive the state.

Look again at what supersession is. Two statements conflict, and the
later one wins. That is lesson 18's shape, an exception overriding a
default, with the priority decided by date. Here it takes `not` and
`min` to express, which is why this program has three strata.

## Why, and why not, with dates in them

A derivation now includes the comparisons that let it through:

```
$ python3 datalog.py --explain 'holds_at(alice, works_at, globex, "2024-01-01")' programs/employment.dl
?- explain holds_at(alice, works_at, globex, "2024-01-01")
   holds_at(alice, works_at, globex, "2024-01-01")   [via holds_at(E, R, O, T) :- until(E, R, O, F, U), asked(T), F <= T, T < U.]
     until(alice, works_at, globex, "2022-07-15", "9999-12-31")   [via until(E, R, O, F, "9999-12-31") :- said(E, R, O, F), not ended(E, R, O, F).]
       said(alice, works_at, globex, "2022-07-15")   (base fact)
       not ended(alice, works_at, globex, "2022-07-15")   (absent from its completed stratum)
     asked("2024-01-01")   (base fact)
     "2022-07-15" <= "2024-01-01"   (comparison)
     "2024-01-01" < "9999-12-31"   (comparison)
```

And the negative question names the date that failed:

```
$ python3 datalog.py --explain 'holds_at(alice, works_at, acme, "2024-01-01")' programs/employment.dl
?- explain holds_at(alice, works_at, acme, "2024-01-01")
   holds_at(alice, works_at, acme, "2024-01-01") is not derived.  Per rule:
     via holds_at(E, R, O, T) :- until(E, R, O, F, U), asked(T), F <= T, T < U.
       blocked at: "2024-01-01" < "2022-07-15" -- the comparison is false
```

Alice's Acme interval closed on 2022-07-15. If a caseworker asks why
the system thinks Alice left Acme, those two outputs are the complete
answer: the statement that ended it, and the date it ended.

## Intervals: who overlapped with whom

Once facts have intervals, the natural questions are about how
intervals relate. Two intervals overlap exactly when each starts
before the other ends, which is two comparisons:

```prolog
colleagues(X, Y, C) :- until(X, works_at, C, F1, U1),
                       until(Y, works_at, C, F2, U2),
                       X < Y, F1 < U2, F2 < U1.
```

(`X < Y` on names keeps one copy of each pair and excludes `X = Y`.)

```
$ python3 datalog.py -q 'colleagues(X, Y, C)' programs/employment.dl
?- colleagues(X, Y, C)
   colleagues(alice, bob, acme).
   colleagues(alice, carol, globex).
   (2 answers)
```

Bob was at Acme from 2020-05 to 2021-09, inside Alice's time there.
Carol is still at Globex and so is Alice, so their intervals both end
at the sentinel and overlap from 2022-07-15 on. Allen's interval
algebra names thirteen ways two intervals can relate (before, meets,
overlaps, during, and so on). Every one of them is a few comparisons
between endpoints, so all thirteen can be written as rules like this
one.

## A mistake the engine can see

Interval tests are easy to get subtly wrong, and one slip is common
enough to check for. `programs/employment-typo.dl` has `T < F` where
`T < U` was meant:

```
$ python3 datalog.py -q 'holds_at(E, R, O, T)' programs/employment-typo.dl
warning: F <= T, T < F cannot all hold, so this rule can never fire: holds_at(E, R, O, T) :- until(E, R, O, F, U), asked(T), F <= T, T < F.
?- holds_at(E, R, O, T)
   (0 answers)
```

No answers is a legal answer, so without the warning this would look
like a quiet day. The check behind it is small. Each comparison is an
edge between two terms (`a <= b`, strict for `<`), constants are
chained in their own order, and the comparisons contradict each other
exactly when some cycle of edges includes a strict one. That is the
strongly-connected-component search stratification already uses, run
on terms instead of predicates. (Lesson 14 mentioned clingo paired with
a difference-logic solver. This is the smallest piece of that idea.)

## Two clocks: what we knew, and when

So far each statement has had one date, when it took effect. Records
have a second date: when the statement was *written down*. The two
differ all the time. Bob moved to Initech on 2021-09-01, but HR filed
it on 2021-11-15:

```prolog
%     subject  relation  object   effective     recorded
said(bob,   works_at, acme,    "2020-05-01", "2020-05-01").
said(bob,   works_at, initech, "2021-09-01", "2021-11-15").   % filed late
```

The October payroll ran on 2021-10-01 and paid Bob as an Acme employee.
Was that a mistake? It was wrong about the world, and right given what
anyone knew that day. Telling those apart needs both dates, which is
called **bitemporal** data: **valid time** (when it was true) and
**transaction time** (when we recorded it).

`programs/employment-bitemporal.dl` asks questions of the form "as
known on K, what held on T?" It filters the statements to those
recorded by K, then runs the same supersession rules as before, with K
threaded through every predicate:

```prolog
view("2021-10-01", "2021-09-30").   % the October payroll run, as it ran
view("2024-01-01", "2021-09-30").   % the same day, as we know it now

known(E, R, O, F, K) :- said(E, R, O, F, Rec), view(K, _), Rec <= K.
```

```
$ python3 datalog.py -q 'holds_at(bob, works_at, C, "2021-09-30", K)' programs/employment-bitemporal.dl
?- holds_at(bob, works_at, C, "2021-09-30", K)
   holds_at(bob, works_at, acme, "2021-09-30", "2021-10-01").
   holds_at(bob, works_at, initech, "2021-09-30", "2024-01-01").
   (2 answers)
```

Same day, two answers, both correct. The first is what the payroll run
saw; the second is what we know now. An auditor needs the first, and a
back-pay calculation needs the gap between them. A system that only
keeps current state can produce neither.

Two widely used systems are built on this idea. Datomic is a Datalog
database in which every fact carries the transaction that asserted it,
and a query can be run against the database `as-of` any past
transaction. The SQL:2011 standard added both kinds of time to SQL
tables: *system-versioned* tables record transaction time, and
*application-time periods* record valid time. Both use half-open
intervals and far-future sentinels, as this lesson does.

## The price: time only moves forward, and conclusions do not

Every new statement is an insertion. You might expect lesson 10's
incremental engine to handle it cheaply. It refuses this program:

```
$ python3 incremental.py programs/employment.dl
error: incremental maintenance supports positive, aggregate-free programs only (negation and aggregation are non-monotone; maintaining them is where the modern theory earns its keep): ends(E, R, O, F, min(U)) :- superseded(E, R, O, F, U).
```

That refusal is the lesson in miniature. Adding Alice's Globex
statement *removed* a conclusion: Alice no longer works at Acme from
2022 onwards. An insertion that retracts conclusions is exactly the
non-monotone update that semi-naive resumption cannot handle, because
it only ever adds. The base engine recomputes from scratch instead,
which takes milliseconds at this scale. Engines that do this
incrementally at scale either track each fact's support precisely
(DBSP, from lesson 10) or recompute only the
predicates downstream of what changed, which is what memory engines
built for language-model agents do (lesson 24).

## Exercises

1. Bob goes back to Acme: add
   `said(bob, works_at, acme, "2023-04-01").` Predict Bob's `until`
   facts, and whether `colleagues` gains a row, before running it.
2. Some systems store intervals outright, as
   `employed(Person, Employer, From, Until)`. Write two integrity
   constraints (lesson 17) for such a table: no period closes before
   it opens, and nobody has two employers at once. Make sample data
   that breaks each one.
3. `holds_at` only answers for the dates in `asked/1`. Why can it not
   simply answer "for every date"? Name the lesson whose rule stops
   you.
4. A statement can be entered in error. Add
   `withdrawn(Subject, Relation, Object, Effective, Recorded)` to the
   bitemporal program, so a withdrawn statement disappears from views
   known after the withdrawal and stays in views from before it.
5. Add `said(alice, works_at, acme, "2019-06-01").`, a second statement
   that Alice works at Acme. What happens to her `until` facts, and to
   `holds_at`? Is anything wrong?

Next: [lesson 24](24-memory.md), where a language model writes the
statements, and the rules from lessons 8, 17 and this one decide what
it remembers.
