# Lesson 17 — Writing rules that survive review

Fifteen lessons have been about how engines evaluate rules. This one is
about writing them, which is a different skill and the one the rest of
the course implies: the README's whole case is that rules get reviewed,
audited, and inherited by someone who did not write them.

The drafting habits themselves were met one at a time along the way —
negate one thing, not a relation with a spare variable (Lesson 3);
negating base facts is free, negating derived predicates forces an
order (Lesson 3); several models means a choice unmade (Lesson 5); mind
the rows that produce no group (Lesson 13); when you want "for all",
derive the counterexample and negate it one stratum up (Lesson 6); ask
whose authority says this is absent (Lesson 4). What no single lesson could show is the
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
% programs/lending-draft1.dl
may_borrow(P) :- member(P), not overdue(P, B).
```

```
$ python3 datalog.py programs/lending-draft1.dl
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
% programs/lending-draft2.dl
may_borrow(P) :- member(P), not has_overdue(P), not suspended(P).
may_borrow(P) :- staff(P).
```

That evaluates cleanly, and gives the wrong answer:

```
$ python3 datalog.py -q 'may_borrow(P)' programs/lending-draft2.dl
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
$ python3 datalog.py --explain 'may_borrow(kim)' programs/lending-draft2.dl
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

One more question became askable the moment the drafts were fixed:
the *negative* one. Kim no longer borrows — but a caseworker will ask
why not, and "the rules don't derive it" is no answer. Ask the engine:

```
$ python3 datalog.py --explain 'may_borrow(kim)' programs/lending.dl
?- explain may_borrow(kim)
   may_borrow(kim) is not derived.  Per rule:
     via may_borrow(P) :- member(P), not has_overdue(P), not suspended(P).
       blocked at: not suspended(kim) -- suspended(kim) holds:
         suspended(kim)   (base fact)
     via may_borrow(P) :- staff(P), not suspended(P).
       blocked at: not suspended(kim) -- suspended(kim) holds:
         suspended(kim)   (base fact)
```

Every rule that could have granted it, and the exact premise where
each one died — with the blocking fact's own derivation inlined when
the blocker is a negation that *held*. Why-not is the other half of
provenance, and it turns "the answer looks wrong" into "this literal,
this fact."

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
| Why is this *missing*? | `--explain` the absent fact | every rule's first failing literal, blockers explained |

The fourth is the one people skip. A redundant rule is rarely harmless:
it usually means you wrote the same condition twice in different words,
and only one of them will get updated when the policy changes.

## A performance habit: the guard, and where to put it

One habit is about speed rather than correctness, nobody teaches it,
and it is worth more than an index. Suppose you want pairs of deployed
services sharing a dependency, over Lesson 2's supply chain (160
packages, 8,457 `uses` facts, 12 services). Four ways to write one
rule, measured on this engine:

| Body | Time | Answers |
|---|---|---|
| `uses(X, L), uses(Y, L)` | 38.4s | 25,281 |
| `service(X), service(Y), uses(X, L), uses(Y, L)` | 55.2s | 144 |
| `service(X), uses(X, L), uses(Y, L), service(Y)` | **8.3s** | 144 |
| `uses(X, L), uses(Y, L), service(X), service(Y)` | 43.8s | 144 |

Row one is the unguarded rule: it asks about *all* packages when you
wanted services, and pays for 25,281 answers you will throw away. But
look at row two before reaching for guards as a slogan: both guards up
front is *slower than no guard at all*, because with X and Y fixed the
engine re-scans the whole `uses` relation for every one of the 144
pairs. Row three is the craft: **each variable is restricted just
before it multiplies** — X pinned to a service, X's dependencies
enumerated once, Y found *through* the shared dependency, then
checked. Same answers, four and a half times faster than no guard,
nearly seven times faster than the clumsy guard.

(Diagnosing this no longer needs a stopwatch: `--trace` ends by
naming the hottest rules with their share of the run, and the
unguarded rule above shows up at the top of that list instantly.)

Two honest notes. This engine joins strictly left to right (Lesson 2's
*Under the hood*), so literal order is entirely yours; engines with
optimisers reorder bodies for you, and there the guard's *presence*
matters more than its position — but the domain restriction itself is
a modelling fact no optimiser can invent. And guards are the manual
half of a story whose automatic half you have met: magic sets
(Lesson 7) restricts computation to what a *query* demands; a guard
restricts it to what the *rule* means. Write the guard first, and let
the rewriting multiply it.

## The rules will outlive the engine, too

This course's pitch is that rules outlive the query. They also outlive
the *engine*, and there is no standard Datalog. The portable core is
what Lessons 1–3 taught — Horn clauses, stratified negation — and
almost everything else is dialect: type systems, aggregation syntax,
arithmetic and its modes, functors and record extensions. Real
multi-thousand-rule codebases have been ported between dialects, and
the reports agree on where it bites first: the type system and value
construction, not the logic.

Types deserve their own sentence, because this engine's lack of them
is an honest cost, not a virtue. Soufflé is typed; here, joining two
relations on the wrong column is not an error — it is an empty (or
quietly wrong) result, discovered by staring. Arity mistakes are
caught; *meaning* mistakes in column position are exactly what a type
system would catch and nothing here does. On a fifty-rule policy you
will not notice; at Doop scale — thousands of rules — it is the first
thing practitioners miss.

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
   automatically". You cannot count without Lesson 13's aggregation —
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

Next (optional): [the road not taken](18-category-theory.md) — what
the course's mathematics actually is, for readers who want the frame
named.
