# Lesson 16 — Writing rules that survive review

Fifteen lessons have been about how engines evaluate rules. This one is
about writing them, which is a different skill and the one the rest of
the course implies: the README's whole case is that rules get reviewed,
audited, and inherited by someone who did not write them.

The drafting habits themselves were met one at a time along the way —
negate one thing, not a relation with a spare variable (Lesson 3);
negating base facts is free, negating derived predicates forces an
order (Lesson 3); several models means a choice unmade (Lesson 5); mind
the rows that produce no group (Lesson 12); ask whose authority says
this is absent (Lesson 4). What no single lesson could show is the
habits *working together on one policy*, which is this lesson's job.

We will write a small policy badly twice, and let the engine find both
faults.

## The policy, in English

> Members may borrow, unless they have an overdue loan or are
> suspended. Staff may borrow whether or not they have overdue loans —
> but a suspension applies to everybody.

Four people. Iris is an ordinary member in good standing. Jon is a
member with an overdue book. Kim is a member, on the staff — and
suspended. Lena is a member, on the staff, and has an overdue book of
her own. So the roster contains one clean case and three tests: an
overdue member, a suspended staffer, and an overdue staffer.

## Draft 1, and the engine refuses it

The obvious first attempt:

```prolog
may_borrow(P) :- member(P), not overdue(P, B).
```

```
$ python3 datalog.py draft1.dl
error: unsafe rule: variable B of negated literal not overdue(P, B) is not
bound by a positive literal in: may_borrow(P) :- member(P), not overdue(P, B).
```

The engine will not guess what `B` means. You wrote "has no overdue
loan", but `not overdue(P, B)` with `B` free asks something else
entirely, and the two readings differ: *no overdue loan at all* versus
*some particular book they do not have out*. Safety (Lesson 3) exists
to stop that ambiguity reaching evaluation.

The fix is to say which one you meant, by projecting first:

```prolog
has_overdue(P) :- overdue(P, _).
may_borrow(P)  :- member(P), not has_overdue(P).
```

**Habit:** when you negate, negate a *proposition about one thing*, not
a relation with a spare variable in it. If the negated atom has a
variable that appears nowhere else, you have not finished modelling.

## Draft 2, which runs, and is wrong

Now add the staff exemption. Staff may borrow despite overdue loans, so
the natural move is a second rule:

```prolog
may_borrow(P) :- member(P), not has_overdue(P), not suspended(P).
may_borrow(P) :- staff(P).
```

That evaluates cleanly, and gives the wrong answer:

```
$ python3 datalog.py -q 'may_borrow(P)' draft2.dl
?- may_borrow(P)
   may_borrow(iris).
   may_borrow(kim).
   may_borrow(lena).
   (3 answers)
```

Iris is right, and Lena is right — staff, overdue, borrowing anyway is
exactly what the exemption is for. But Kim is suspended, and the
policy says suspension applies to everybody. Why is she borrowing?

```
$ python3 datalog.py --explain 'may_borrow(kim)' draft2.dl
?- explain may_borrow(kim)
   may_borrow(kim)   [via may_borrow(P) :- staff(P).]
     staff(kim)   (base fact)
```

There is the whole bug in three lines. The derivation names the rule
that fired and lists everything it consumed, and the suspension check
is simply not in it. Not "the answer looks wrong": *this* rule, with
*this* premise, and nothing else.

This is what a derivation is for. A test would have told you the answer
was wrong; the derivation tells you which of your two rules is wrong,
before you go looking.

**Habit:** an exemption is a *narrower* rule, not an unconditional one.
Every escape hatch needs the conditions that apply to everybody.

## Draft 3

```prolog
% programs/lending.dl
has_overdue(P) :- overdue(P, _).

may_borrow(P) :- member(P), not has_overdue(P), not suspended(P).
may_borrow(P) :- staff(P), not suspended(P).
```

```
$ python3 datalog.py -q 'may_borrow(P)' programs/lending.dl
?- may_borrow(P)
   may_borrow(iris).
   may_borrow(lena).
   (2 answers)
```

Kim is gone — and only Kim. The count dropping from three to two is
what a test would have caught; which name dropped, and why, is what
the derivations show. Lena still borrows, and her tree is the
exemption doing its honest work, guard included:

```
$ python3 datalog.py --explain 'may_borrow(lena)' programs/lending.dl
?- explain may_borrow(lena)
   may_borrow(lena)   [via may_borrow(P) :- staff(P), not suspended(P).]
     staff(lena)   (base fact)
     not suspended(lena)   (absent from its completed stratum)
```

Ask why Iris qualifies and every condition is stated, including the
negative ones:

```
$ python3 datalog.py --explain 'may_borrow(iris)' programs/lending.dl
?- explain may_borrow(iris)
   may_borrow(iris)   [via may_borrow(P) :- member(P), not has_overdue(P), not suspended(P).]
     member(iris)   (base fact)
     not has_overdue(iris)   (absent from its completed stratum)
     not suspended(iris)   (absent from its completed stratum)
```

## The checklist

Five questions, all mechanical, all cheap. Run them before you ask
anyone to review a rule set.

| Ask | How | If it fails |
|---|---|---|
| Is it well-formed? | it runs at all | safety error names the variable |
| Is it circular? | it runs at all | stratification names the cycle |
| Does it have exactly one answer? | `--models` | none = contradictory, several = you left a choice unmade |
| Any rule doing no work? | `containment.py` | a redundant rule is usually a modelling mistake |
| Does the reason read correctly? | `--explain` on a surprising answer | the derivation names the rule at fault |

The fourth is the one people skip. A redundant rule is rarely harmless:
it usually means you wrote the same condition twice in different words,
and only one of them will get updated when the policy changes.

## Two failure modes the checklist will not catch

**Absence you did not model.** `not suspended(P)` means the suspension
table never said so. If suspensions live in a system that was down when
you loaded the data, everybody borrows, and every derivation is
immaculate. Lesson 4 is entirely about this, and the habit it leaves
you with is the one to carry into review: *when you see `not`, ask
whose authority says this is absent.*

**Rules that are coherent and wrong.** Nothing here checks the policy
against what anybody intended. The engine will tell you your rules
agree with each other; only a person can tell you they agree with the
regulation. That is the division of labour, and it is why the
derivation matters; it makes the human's remaining job small enough to
actually do.

## Exercises

1. Add "a member with more than two overdue loans is suspended
   automatically". You cannot count without Lesson 12's aggregation —
   write it with `count`, then check whether the program still
   stratifies and explain the result.
2. Draft 2 had two rules where one silently overrode the other. Write a
   version where the *order* of the rules seems to matter, then explain
   why it cannot.
3. Someone proposes `may_borrow(P) :- member(P), not blocked(P).` and
   `blocked(P) :- member(P), not may_borrow(P).` Predict what
   `--models` says before running it.
4. Take a policy you actually work with, model its first paragraph, and
   run the five checks. The interesting output is not the answer — it
   is which question you could not express.

Next (optional): [the road not taken](17-category-theory.md) — what
the course's mathematics actually is, for readers who want the frame
named.
