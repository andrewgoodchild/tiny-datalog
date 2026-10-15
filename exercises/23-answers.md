# Lesson 23 — answers

Runnable rules: `exercises/23-answers.dl` (exercise 2) and
`exercises/23-withdrawn.dl` (exercise 4).

**1. Bob goes back to Acme.**

Bob gets three intervals:

```
until(bob, works_at, acme, "2020-05-01", "2021-09-01").
until(bob, works_at, acme, "2023-04-01", "9999-12-31").
until(bob, works_at, initech, "2021-09-01", "2023-04-01").
```

The first Acme statement is still ended by Initech, because
supersession needs a *different* value (`O != O2`), and the earliest
different value after 2020-05-01 is Initech's 2021-09-01. The new
statement ends Initech and is itself open. `colleagues` does not
change: Bob's second Acme interval starts in 2023, after Alice left
Acme in 2022-07, so the two intervals do not overlap. A rehire is two
intervals at the same employer, which is what HR systems record too.

**2. Constraints for stated intervals.**

```prolog
:- employed(P, C, F, U), U <= F.
:- employed(P, C1, F1, U1), employed(P, C2, F2, U2), C1 < C2,
   F1 < U2, F2 < U1.
```

The first catches an interval typed backwards (and an empty one, from
`U = F`). The second is the overlap test from the lesson, applied to
one person's intervals at two employers. `C1 < C2` reports each
clashing pair once instead of twice, and leaves two periods at the
*same* employer alone: adjacent periods at one employer are normal,
and overlapping ones are a different question (exercise 5). Run on
the answer file's data, ann's Globex start is a month early and ben's
period is backwards:

```
$ python3 datalog.py exercises/23-answers.dl
constraint violated: :- employed(P, C, F, U), U <= F.
   employed(ben, initech, "2022-03-01", "2022-02-01"), "2022-02-01" <= "2022-03-01"
   (1 counterexample)
constraint violated: :- employed(P, C1, F1, U1), employed(P, C2, F2, U2), C1 < C2, F1 < U2, F2 < U1.
   employed(ann, acme, "2020-01-01", "2021-06-30"), employed(ann, globex, "2021-06-01", "9999-12-31"), acme < globex, "2020-01-01" < "9999-12-31", "2021-06-01" < "2021-06-30"
   (1 counterexample)
```

The second counterexample shows the exact pair of dates that overlap,
2021-06-01 to 2021-06-30. Notice that the comparisons in a
counterexample are the conditions that *held*; they are part of the
evidence, not noise.

The contrast with the lesson's program is worth stating. There,
intervals are *derived* from statements, so they cannot overlap: the
rules close one interval exactly where the next opens. Here they are
*stated*, so they can be wrong in any way a person can type, and
constraints are how you find out.

**3. Why not every date?**

`holds_at(E, R, O, T) :- until(E, R, O, F, U), F <= T, T < U.` leaves
`T` bound by nothing but comparisons, and lesson 3's safety rule
refuses it (in lesson 14's terms, the comparison's mode needs both
sides bound). The relation it would define is infinite: every date in
every interval, and `"9999-12-31"` makes most intervals very long.
What you can have is the finite description, which is `until/5`
itself. Ask whether a given date falls inside it, by binding `T` with
a fact.

**4. Withdrawn statements.**

```prolog
withdrawn(carol, works_at, initech, "2021-08-01", "2021-12-01").

known(E, R, O, F, K) :- said(E, R, O, F, Rec), view(K, _), Rec <= K,
                        not withdrawn_by(E, R, O, F, K).
withdrawn_by(E, R, O, F, K) :- withdrawn(E, R, O, F, W), view(K, _), W <= K.
```

A withdrawal is not a deletion. It is another statement with its own
recorded date, so the October 2021 view still sees the mistake, which
is what the system believed then:

```
$ python3 datalog.py -q 'holds_at(carol, works_at, C, "2021-09-30", K)' exercises/23-withdrawn.dl
?- holds_at(carol, works_at, C, "2021-09-30", K)
   holds_at(carol, works_at, globex, "2021-09-30", "2024-01-01").
   holds_at(carol, works_at, initech, "2021-09-30", "2021-10-01").
   (2 answers)
```

In October the system believed Carol had moved to Initech, and the
answer as known now is Globex. That pair is exactly what an auditor
asking "why was Carol's pay routed to Initech's cost centre?" needs.

**5. The same thing said twice.**

Both Acme statements are superseded by Globex, so Alice gets two Acme
intervals, `["2019-03-01", "2022-07-15")` and
`["2019-06-01", "2022-07-15")`. They overlap, and `holds_at` is
unaffected, because it is a set: Alice works at Acme on 2021-06-30
whichever interval says so. Nothing is wrong logically. But `until`
now has more rows than there were periods of employment, and any
aggregate over it, such as counting stints or summing days employed,
would double-count. Merging overlapping or adjacent intervals with the
same value into one is called **coalescing**. It needs the endpoints
of a *group* of intervals, which takes `min`, `max` and a recursive
"these two touch" relation, and it is a good test of lesson 13.
