# Lesson 4 — Closed and open worlds, and what null means

This repository contains two reasoners, and they disagree about the
most basic question a knowledge system faces: **what does it mean that
something isn't there?**

- `datalog.py` — the engine you have been using — says: *absent means
  false.* If I cannot derive `employed(dana)`, then `not
  employed(dana)` succeeds.
- `subsumption.py` — Lesson 12's ontology classifier, which you can
  treat as a black box today — says: *absent means unknown.* If the
  ontology never says fathers are tall, it does not conclude they
  aren't. It concludes nothing.

(This is Lesson 3's missing half. The two demo commands below need no
knowledge of how the classifier works, only of what it concludes —
Lesson 12 builds it properly.)

Neither is wrong. They are answers to different questions, and knowing
which one you are standing in is the difference between a benefits
system that works and one that quietly pays the wrong people.

## The closed world, and its trap

Datalog runs on the **closed-world assumption (CWA)**: *any fact that
cannot be derived from the database is taken to be false.* The name
and the formal statement are Raymond Reiter's, from 1978 — published,
fittingly, in the same Gallaire–Minker volume that founded the field
(Lesson 0). It is an assumption about *completeness*: the database is
declared to be the whole truth, so absence of a fact is evidence, not
silence.

That is what makes negation computable at all (Lesson 3), and for a
database it is usually right — if a row is missing from `employed`,
that person genuinely isn't employed, because that table is the
authority.

Usually. `programs/missing-data.dl` has three people in a qualifying
household: Cyril, checked and employed; Bob, checked and not; and Dana,
whose file is simply empty.

```prolog
eligible_naive(P) :- member(P, H), qualifying_household(H),
                     not employed(P).
```

```sh
$ python3 datalog.py programs/missing-data.dl
% eligible_naive/1 (derived) — 2 facts
eligible_naive(bob).
eligible_naive(dana).
```

Dana gets the benefit. Worse, she gets it with a flawless justification:

```sh
$ python3 datalog.py --explain 'eligible_naive(dana)' programs/missing-data.dl
   ...
     not employed(dana)   (absent from its completed stratum)
```

Read that last line carefully; it is the honest one. The engine is not
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

Now `eligible(bob)` and `pending(dana)`: a third outcome, which is the
true state of the world. The general move: **model the check, not just
the result.** Any time you write `not p(X)` against data that might
merely be missing, you want a companion predicate asserting that the
question was actually asked.

## The registry trap

The same trap has an institutional shape worth naming: the
**registry**. Every organisation keeps catalogues of things — an API
registry, an asset inventory, a list of deployed services — and every
such catalogue invites the closed-world reading: *not in the registry,
so it doesn't exist*. But a registry's absence speaks only with the
registry's authority, and registries are almost never authorities over
the world they describe — the unregistered service is still running
(ask any security team about shadow IT). The question to ask of a
catalogue is the question this lesson keeps asking of a table: *what
process guarantees that everything true gets written here?* Where
there is such a process, closed-world reasoning over the registry is
sound; where there isn't, model the registry's *coverage* explicitly,
exactly as `employment_checked` modelled the check.

## The open world, next door

`subsumption.py` reasons about definitions rather than data, and there
is no "complete" list of everything true about fathers. So it makes
the **open-world assumption (OWA)**: *a fact that is neither stated
nor derivable is not false — it is unknown.* The axioms are read as a
partial description of a larger world, so absence of proof is never
proof of absence. It will never tell you
`father ⊑ not tall`; it cannot even express that — the classifier has
disjointness (⊥), but no general negation on concepts (Lesson 12's
limits section).

The consequence is worth seeing rather than being told, because it is
the sharpest observable difference between the two engines. Add
information to each and watch what happens to the conclusions.

**Closed world — adding a fact destroys a conclusion:**

```sh
$ python3 datalog.py -q 'flies(X)' programs/tweety.dl
   flies(tweety).
   (1 answer)

$ (cat programs/tweety.dl; echo 'penguin(tweety).') > /tmp/t.dl
$ python3 datalog.py -q 'flies(X)' /tmp/t.dl
   (0 answers)
```

**Open world — adding an axiom can only create conclusions:**

```sh
$ python3 subsumption.py -q father programs/family-ontology.dl
father  ⊑  man, parent, person

$ (cat programs/family-ontology.dl; echo 'isa(father, taxpayer).') > /tmp/o.dl
$ python3 subsumption.py -q father /tmp/o.dl
father  ⊑  man, parent, person, taxpayer
```

That is **non-monotonicity** versus **monotonicity**, and it is not a
quirk of these implementations; it is forced by the two assumptions.
Under the closed-world assumption (CWA), new facts can shrink what
"absent" covers, so conclusions can be withdrawn. Under the open-world
assumption (OWA), nothing was ever concluded from absence,
so nothing has to be taken back.

## No nulls, by design

Most systems have a *presence that marks absence* — a null. Datalog
has none: a fact is a ground atom, and if you don't know a value, you
don't write the fact. SQL's nullable column

```sql
person(id, name, phone NULL)
```

decomposes into narrow relations:

```prolog
person(p1, "iris").
phone(p1, "555-0100").     % no phone? then no phone fact
```

A nullable column is really an *optional relation*, and Datalog makes
you say so. (Datomic works exactly this way in production: an absent
attribute is simply no datom.) Asking "who has no phone" then runs
through this course's own moves: project first (`has_phone(P) :-
phone(P, _).`, Lesson 3's spare-variable habit), and remember that
`not has_phone(P)` reads this lesson's checking assumption — no phone
*recorded*.

That is the whole design position; the comparative tour — SQL's one
marker carrying three meanings and the three-valued logic that bills
for it, database theory's self-identical labelled nulls, Hoare's
billion-dollar reference — waits for [Lesson 18](18-neighbours.md),
where the neighbours get their due. The sentence to carry out of *this*
lesson: SQL's NULL-as-unknown smuggles one open-world cell into a
closed-world table, and every nullable column is quietly asking the
question this lesson taught you to ask.

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
which is a different logic with different guarantees. That layering
has a name — the **ontology-plus-rules hybrid** — and this repository
is one: closed-world rules (this engine) over an open-world
terminology (Lesson 12's classifier), each doing the job the other
cannot. When you need both, you run both, and you keep the boundary
explicit — which is precisely what the porting trap below is about
failing to do.

## The porting trap

The practical hazard is moving rules between the two worlds without
noticing. A policy written as Datalog rules and then "represented" in
an ontology does not mean the same thing: every `not` silently changes
from "we checked and it's false" to something the ontology cannot say
at all. The reverse is worse — ontology axioms loaded into a rule
engine acquire a completeness claim nobody made.

If you take one habit from this lesson: when you see `not` in a rule,
ask *whose authority says this is absent*, and if the answer is "no
one, the row just isn't there", you have found a bug waiting.

## Exercises

1. Add `employment_checked(dana).` to `programs/missing-data.dl` and
   predict all three relations before running it. Which of Dana's three
   possible states is now recorded?
2. The `pending` rule uses `not employment_checked(P)`, which is
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
5. Take a real schema you know with a nullable column. Decide which
   flavour(s) its nulls actually carry — unknown, inapplicable,
   withheld, or several at once — then decompose it into Datalog
   relations, adding a knowledge-state predicate where the flavour
   demands one. What did the decomposition force you to decide that
   the schema let you postpone?

Next: [beyond stratification](05-beyond-stratification.md) — Lesson
3's cliffhanger: the rejected programs that turn out to be meaningful,
and the semantics that tells them apart.
