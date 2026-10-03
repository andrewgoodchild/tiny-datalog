# Lesson 18 — Rules with exceptions: defeasible logic

Lesson 3 handled an exception with `not`: birds fly unless abnormal.
Lesson 17 wrote a whole policy that way, and the drafting habit it
ended with — *an exemption is a narrower rule, not an unconditional
one* — was a rule about where to put the `not`s. Every exception had
to be written into every rule it overrides, by hand, and when a draft
got that wrong the engine said nothing: draft 2's staff exemption
silently beat the suspension rule, because a `not` was missing.

Real rule sets are mostly made of this. A statute states a general
rule, then exceptions, then exceptions to the exceptions, and lawyers
have names for the tie-breaks — the specific beats the general (*lex
specialis*), the later beats the earlier (*lex posterior*). This
lesson is about a logic in which an exception is a rule, a priority is
a fact, and a conflict nobody resolved is reported instead of decided
by accident.

## Four kinds of statement

**Defeasible logic** is Donald Nute's (1994). A theory has facts and
three kinds of rule, plus an order on rules:

```prolog
% programs/birds.dfl
bird(tweety).   penguin(opus).   bird(freddie).   injured(freddie).

r1: penguin(X) -> bird(X).      % strict: no exceptions
r2: bird(X)    => flies(X).     % defeasible: birds usually fly
r3: penguin(X) => ~flies(X).    % penguins usually don't
r4: injured(X) ~> ~flies(X).    % a defeater: casts doubt, proves nothing

r3 > r2.
```

- A **strict** rule `->` is classical: if the body holds, so does the
  head, whatever else is true.
- A **defeasible** rule `=>` says *usually*: its conclusion stands
  unless something defeats it.
- A **defeater** `~>` can only attack. It blocks a conclusion without
  supporting the opposite one.
- **Superiority** `r3 > r2` says which rule wins when two disagree.

`~` is *strong* negation: `~flies(opus)` is a claim about Opus, not the
absence of one. A conflict is exactly a pair `p`, `~p`. There is no
`not` anywhere, and that is the design: absence is not evidence, rules
attack rules, and priorities say who wins. The notation is the one the
papers use, and the one the SPINdle reasoner reads (which also marks
facts with `>>`).

```
$ python3 defeasible.py programs/birds.dfl
+Δ definitely (5)
   bird(freddie)
   bird(opus)
   bird(tweety)
   injured(freddie)
   penguin(opus)
+∂ defeasibly (7)
   bird(freddie)
   bird(opus)
   bird(tweety)
   flies(tweety)
   ~flies(opus)
   injured(freddie)
   penguin(opus)
−∂ not defeasibly (3)
   flies(freddie)
   flies(opus)
   ~flies(freddie)
undecided (0)
```

Tweety flies. Opus doesn't: `r3` and `r2` both fire, and `r3 > r2`
settles it. Freddie is the defeater's work. `r2` says he flies; `r4`
attacks, and nothing is above `r4`, so `flies(freddie)` falls. But a
defeater supports nothing, so `~flies(freddie)` is not proved either.
The theory says only *we cannot conclude that Freddie flies*, which is
exactly what an injury report licenses.

## Four tags

Each line of that output is a **proof tag**, and there are four
(Antoniou, Billington, Governatori & Maher 2001):

| Tag | Read | Proved when |
|---|---|---|
| +Δ q | definitely q | q is a fact, or a strict rule for q has every body literal +Δ |
| −Δ q | not definitely q | q is not a fact, and every strict rule for q has a body literal −Δ |
| +∂ q | defeasibly q | see below |
| −∂ q | not defeasibly q | the failure of the conditions below is *demonstrated* |

**+∂ q** holds if q is +Δ, or if all three of these hold:

1. some strict or defeasible rule for q has every body literal +∂;
2. `~q` is −Δ, so nothing definite contradicts q;
3. every rule for `~q`, defeaters included, is either **dead** (a body
   literal is −∂) or **beaten** (some applicable rule for q is
   superior to it).

The rule that beats an attacker need not be the rule that supports q,
and different attackers may be beaten by different rules. This is
called **team defeat**: the rules for q win as a team. **−∂ q** is the
exact dual of these conditions.

The minus tags are the subtle part. −∂ q is not "+∂ q was not found".
It is a *finite proof that +∂ q cannot be found*. Most literals end up
with one or the other. The ones that end up with neither are the end
of this lesson.

## Lesson 17's policy, defeasibly

> Members may borrow, unless they have an overdue loan or are
> suspended. Staff may borrow whether or not they have overdue loans —
> but a suspension applies to everybody.

Each sentence becomes one rule, and each "unless" or "but" becomes a
priority:

```prolog
% programs/lending-defeasible-draft.dfl
r1: member(P)      => may_borrow(P).    % members may borrow,
r2: overdue(P, B)  => ~may_borrow(P).   % unless they have an overdue loan;
r3: staff(P)       => may_borrow(P).    % staff may borrow despite that,
r4: suspended(P)   => ~may_borrow(P).   % but a suspension binds everybody.

r3 > r2.
r4 > r1.   r4 > r3.
```

Look at `r2`. Its `B` occurs nowhere else, the very shape Lesson 3
rejected under `not` and Lesson 17 had to project away with
`has_overdue`. Here it is harmless. `r2` is an ordinary positive rule
that fires if there is *some* overdue book, so it means exactly what
the English says.

```
$ python3 defeasible.py -q 'may_borrow(P)' -q '~may_borrow(P)' programs/lending-defeasible-draft.dfl
?- may_borrow(P)
   may_borrow(iris)             +∂
   may_borrow(jon)              −∂
   may_borrow(kim)              −∂
   may_borrow(lena)             +∂
?- ~may_borrow(P)
   ~may_borrow(jon)             −∂
   ~may_borrow(kim)             +∂
   ~may_borrow(lena)            −∂
```

Iris borrows. Kim cannot: the suspension rule beats both rules that
would let her. Lena borrows, by team defeat. `r2` attacks her
borrowing, `r1` cannot answer it, but `r3` is superior and applicable,
and either member of the team may do the beating.

Jon is the interesting row. He is −∂ *both ways*: the theory does not
conclude that he may borrow, and does not conclude that he may not.
`r1` says yes, `r2` says no, and the draft never said which wins. In
Lesson 17, a missing guard was a silent wrong answer. Here a missing
priority is a visible non-answer, and the line that is missing is
exactly the one you need to write:

```prolog
% programs/lending-defeasible.dfl
r2 > r1.   r3 > r2.
r4 > r1.   r4 > r3.
```

```
$ python3 defeasible.py -q '~may_borrow(P)' programs/lending-defeasible.dfl
?- ~may_borrow(P)
   ~may_borrow(jon)             +∂
   ~may_borrow(kim)             +∂
   ~may_borrow(lena)            −∂
```

Compare the two encodings. Lesson 17's draft 3 states the suspension
twice and the overdue check once, each as a `not` placed inside the
rule it restricts. The defeasible version states each condition once,
as a rule, and puts all the precedence in four lines anybody can read
as a list: *overdue beats member, staff beats overdue, suspension
beats both*. Changing the policy means changing one of those lines.

**Habit:** when a rule set has exceptions, list the priorities
explicitly, one per line. A conflict that no priority resolves will
come out −∂ both ways. Read it as a question for whoever owns the
policy, not as a bug.

## Ambiguity: does doubt travel?

Two rules disagree and nothing ranks them. Neither conclusion stands.
Now a third rule depends on one of them:

```prolog
% programs/ambiguity.dfl
r1:      => p.
r2:      => ~p.
r3:      => q.
r4: ~p   => ~q.
```

Should `q` hold? `r4` attacks it, but `r4` rests on `~p`, which is not
established. Defeasible logic has two answers, and both are standard.

```
$ python3 defeasible.py programs/ambiguity.dfl
+Δ definitely (0)
+∂ defeasibly (1)
   q
−∂ not defeasibly (3)
   p
   ~p
   ~q
undecided (0)
```

**Ambiguity blocking**, the default: an attacker counts only if its
body is *proved*. `~p` is not, so `r4` is dead and `q` stands. The
ambiguity is contained where it arose.

```
$ python3 defeasible.py --propagating programs/ambiguity.dfl
+Δ definitely (0)
+∂ defeasibly (0)
−∂ not defeasibly (4)
   p
   ~p
   q
   ~q
undecided (0)
```

**Ambiguity propagating**: an attacker counts if its body is merely
*supported*, meaning there is an argument for it that has not been
beaten. `~p` is supported, so `r4` is live and `q` falls too. Doubt
spreads downstream. This variant, and the *support* tag it needs, are
in Maher (2012).

Which is right depends on what a wrong conclusion costs. Blocking
concludes more. Propagating is more cautious, and suits domains where
acting on a contested premise is worse than not acting.

## What it will not settle

```
$ python3 defeasible.py programs/loops.dfl
+Δ definitely (0)
+∂ defeasibly (0)
−∂ not defeasibly (1)
   ~p
undecided (4)
   a
   b
   p
   q
```

The file holds two loops. `a => b. b => a.` with nothing to start it:
proving `b` needs `a`, refuting `b` needs `a` refuted first, and the
same is true the other way round. Neither tag is ever established.
The second loop runs through a conflict: `p` supports `q`, and `q`
attacks `p`. Whether `p` stands depends on whether `q` does, which
depends on `p`.

Set this beside Lesson 5. The well-founded model would make `a` and
`b` *false*. They form an unfounded set, support that only goes round
in a circle, and the well-founded semantics was invented to cut
exactly that. Defeasible logic does not cut it. Maher and Governatori
(1999) showed why: standard defeasible logic is characterised by
*Kunen's* three-valued semantics of a logic program encoding the
theory, and Kunen's semantics has no notion of unfounded sets. They
also defined a **well-founded defeasible logic**, which adds unfounded
sets and does refute `a` and `b`. So "undecided" is a property of the
chosen semantics, not of the theory. Lesson 5 made the same point
about stable models.

The module departs from the proof theory in one place, and says so.
It grounds the theory the way `semantics.py` does, instantiating each
rule only where something could make its body true. A loop written
with variables that nothing ever starts, such as
`a(X) => b(X). b(X) => a(X).`, is therefore never instantiated, and is
not reported at all. The proof theory, ranging over every constant,
would leave each instance undecided. A loop written without variables,
like the one above, needs no instantiating and comes out undecided as
the theory says.

## Where it sits

**Cost.** Propositional defeasible logic runs in time linear in the
size of the theory (Maher 2001), which is better than stable models
and in line with stratified Datalog. This module is not that
algorithm. It grounds the theory, then re-checks every literal against
the proof conditions until nothing changes. That is polynomial but far
from linear, and it keeps the code a direct transcription of the
conditions.

**Neighbours.** SPINdle (Lam & Governatori 2009) is the reference
implementation, with the syntax used here. Delores and Deimos (Maher
et al. 2001) are the earlier pair: one computes everything bottom-up
in linear time, the other answers queries top-down. *Defeasible logic
programming* (DeLP, García & Simari 2004) sounds the same and is not.
It builds arguments and compares them by *specificity*, so a more
specific rule wins without being told to. Defeasible logic never
infers a priority; you state every one. The external conformance
corpus in [`conformance/`](../conformance/README.md) checks this
module against cases from SPINdle and from the papers. The cases
checked against DeLP disagree with it exactly where specificity
decides the answer.

**When to reach for it.** Use it when exceptions and priorities *are*
the content: statutes, regulations, eligibility rules, anything whose
source text says "unless" and "notwithstanding". Plain Datalog with
`not` stays the better tool when the rules are mostly joins and the
exceptions are few, because one semantics is easier to review than
two. A theory with only strict rules is just positive Datalog. The
conformance suite runs 49 such theories, lifted from the core corpus,
and gets the same answers.

## Under the hood

`tiny_datalog/defeasible.py` is a little over 450 lines in three parts.

**Reading.** `Theory.parse` splits the text into statements, recognises
labels, arrows and `>`, and hands each atom to the core parser
(`parse_goal`). Constants, strings, variables and error messages are
therefore the ones the rest of the course uses. `~p` is stored as a
predicate named `~p`, so the core engine never needs to know negation
is special.

**Grounding.** `Theory.ground` reads every rule as if it were strict,
which makes a positive Datalog program, and runs the core engine on
it. The least model is an *envelope*: no tag can ever be about a
literal outside it. Each rule is then instantiated over the envelope
by the core join, `_rule_substitutions`, the same move `semantics.py`
makes before computing stable models.

**Concluding.** `_conclude` transcribes the conditions above one to
one. It computes +Δ and −Δ first, as a fixpoint, then +∂ and −∂. Under
`--propagating` it also computes the support tags (+σ and −σ) in the
same loop, and attackers are judged by those instead. Tags are only
ever added, so the loop stops. The output reports every literal the
theory mentions. "Undecided" is whatever got neither +∂ nor −∂.

## Exercises

1. Add a fifth rule to the lending policy: *a member with a guarantor
   may borrow despite an overdue loan, but not despite a suspension.*
   Which priorities does it need? Predict the table before you run it.
2. Remove `r4 > r3` from `programs/lending-defeasible.dfl`. Who
   changes, and is the result −∂ both ways or undecided? Explain the
   difference between the two.
3. Write Nixon's diamond: Quakers are usually pacifists, Republicans
   usually are not, and Nixon is both. Then add a third rule that
   depends on `pacifist(nixon)`, and compare `--propagating` with the
   default.
4. Lesson 17 ended with a five-question checklist. Which of the five
   questions does defeasible logic answer by itself, and which still
   need a person?
