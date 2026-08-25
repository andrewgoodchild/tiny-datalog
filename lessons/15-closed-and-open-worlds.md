# Lesson 15 — Closed and open worlds

You have now used two reasoners in this repository, and they disagree
about the most basic question a knowledge system faces: **what does it
mean that something isn't there?**

- `datalog.py` says: *absent means false.* If I cannot derive
  `employed(dana)`, then `not employed(dana)` succeeds.
- `subsumption.py` says: *absent means unknown.* If the ontology never
  says fathers are tall, the classifier does not conclude they aren't.
  It concludes nothing.

Neither is wrong. They are answers to different questions, and knowing
which one you are standing in is the difference between a benefits
system that works and one that quietly pays the wrong people.

## The closed world, and its trap

Datalog assumes the database is *complete*: everything true is written
down, so anything unwritten is false. That is what makes negation
computable at all (Lesson 3), and for a database it is usually right —
if a row is missing from `employed`, that person genuinely isn't
employed, because that table is the authority.

Usually. `programs/15-missing-data.dl` has three people in a qualifying
household: Cyril, checked and employed; Bob, checked and not; and Dana,
whose file is simply empty.

```prolog
eligible_naive(P) :- member(P, H), qualifying_household(H),
                     not employed(P).
```

```sh
$ python3 datalog.py programs/15-missing-data.dl
% eligible_naive/1 (derived) — 2 facts
eligible_naive(bob).
eligible_naive(dana).
```

Dana gets the benefit. Worse, she gets it with a flawless justification:

```sh
$ python3 datalog.py --explain 'eligible_naive(dana)' programs/15-missing-data.dl
   ...
     not employed(dana)   (absent from its completed stratum)
```

Read that last line carefully — it is the honest one. The engine is not
claiming Dana is unemployed. It is reporting that `employed(dana)` was
absent from a relation it had finished computing. The rule is what
turned "absent" into "therefore eligible".

## The fix is in the data, not the engine

If absence is meaningful, say so positively:

```prolog
eligible(P) :- member(P, H), qualifying_household(H),
               employment_checked(P), not employed(P).
pending(P) :- member(P, H), qualifying_household(H),
              not employment_checked(P).
```

Now `eligible(bob)` and `pending(dana)` — a third outcome, which is the
true state of the world. The general move: **model the check, not just
the result.** Any time you write `not p(X)` against data that might
merely be missing, you want a companion predicate asserting that the
question was actually asked.

## The open world, next door

`subsumption.py` reasons about definitions rather than data, and there
is no "complete" list of everything true about fathers. So it makes the
opposite assumption: unstated means unknown. It will never tell you
`father ⊑ not tall`; it cannot even express that (Lesson 10's limits
section — no ⊥, no negation at all).

The consequence is worth seeing rather than being told, because it is
the sharpest observable difference between the two engines. Add
information to each and watch what happens to the conclusions.

**Closed world — adding a fact destroys a conclusion:**

```sh
$ python3 datalog.py -q 'flies(X)' programs/03-tweety.dl
   flies(tweety).
   (1 answer)

$ (cat programs/03-tweety.dl; echo 'penguin(tweety).') > /tmp/t.dl
$ python3 datalog.py -q 'flies(X)' /tmp/t.dl
   (0 answers)
```

**Open world — adding an axiom can only create conclusions:**

```sh
$ python3 subsumption.py -q father programs/10-family-ontology.dl
father  ⊑  man, parent, person

$ (cat programs/10-family-ontology.dl; echo 'isa(father, taxpayer).') > /tmp/o.dl
$ python3 subsumption.py -q father /tmp/o.dl
father  ⊑  man, parent, person, taxpayer
```

That is **non-monotonicity** versus **monotonicity**, and it is not a
quirk of these implementations — it is forced by the two assumptions.
Under CWA, new facts can shrink what "absent" covers, so conclusions
can be withdrawn. Under OWA, nothing was ever concluded from absence,
so nothing has to be taken back.

## The trade, stated plainly

| | closed world (Datalog) | open world (description logics) |
|---|---|---|
| absence means | false | unknown |
| adding information | can retract conclusions | only adds conclusions |
| defaults ("unless...") | natural — Lesson 3's Tweety | inexpressible |
| safe when | your data is the authority | you are describing a world you don't contain |
| the failure mode | confident answers from missing data | can't say "normally" about anything |

Each buys exactly what the other cannot afford. **CWA buys you defaults
at the cost of monotonicity; OWA buys you monotonicity at the cost of
defaults.** You cannot have both, and a system that pretends otherwise
is hiding which one it chose.

This explains a fact about medical terminology that looks strange from
the outside: SNOMED CT cannot say "birds normally fly" or "this
treatment is usually indicated". Not because nobody wanted it, but
because the open-world monotone setting that makes a 350,000-concept
classification tractable and stable is the same setting in which
"normally" has no meaning. The defaults live in the rule layer on top,
which is a different logic with different guarantees.

## The porting trap

The practical hazard is moving rules between the two worlds without
noticing. A policy written as Datalog rules and then "represented" in
an ontology does not mean the same thing: every `not` silently changes
from "we checked and it's false" to something the ontology cannot say
at all. The reverse is worse — ontology axioms loaded into a rule
engine acquire a completeness claim nobody made.

If you take one habit from this lesson: when you see `not` in a rule,
ask *whose authority says this is absent* — and if the answer is "no
one, the row just isn't there", you have found a bug waiting.

## Exercises

1. Add `employment_checked(dana).` to `programs/15-missing-data.dl` and
   predict all three relations before running it. Which of Dana's three
   possible states is now recorded?
2. The `pending` rule uses `not employment_checked(P)` — which is
   itself closed-world reasoning about the checking process. When is
   *that* safe, and what would the same objection look like one level
   up?
3. Construct a Datalog program where adding a single fact removes two
   conclusions and adds a third. (Hint: chain a default off another
   default.)
4. Lesson 5's well-founded semantics has a third truth value,
   *undefined*. Is that the same thing as the open world's "unknown"?
   Argue both sides, then say which of the two the `pending` predicate
   above is closer to.

Next: [writing rules](16-writing-rules.md) — sixteen lessons on how
engines evaluate rules, and one on authoring them.
