# Lesson 5 — Beyond stratification: stable models and the café paradox

Lesson 3 ended on a cliffhanger. The engine rejects any program with
negation inside a recursive cycle, but among the rejected programs some
are perfectly meaningful and some are genuinely paradoxical. Telling them
apart needs real semantics. This engine ships both classical answers
behind the `--models` flag.

## Stable models

A set of facts M is a **stable model** (Gelfond–Lifschitz, 1988) if it
justifies itself: assume M is exactly what's true, simplify every `not`
against that assumption, and check that the simplified (now
negation-free) program derives exactly M back. No dropped conclusions, no
unsupported beliefs.

The win/move game (`programs/win.dl`, from Lesson 3) shows why this
is the right notion:

```prolog
move(a, b).  move(b, a).
win(X) :- move(X, Y), not win(Y).
```

```
$ python3 datalog.py --models programs/win.dl
Syntactic check: not stratifiable (win --not--> win).
  (Syntactic only — an unstratifiable program may still have stable models.)
Stable models: 2
  model 1: win(a).
  model 2: win(b).
```

Unstratifiable — yet meaningful: the two stable models are the two
self-consistent ways the game could be. (Answer Set Programming, and the
solver clingo, is this idea industrialized: write programs whose stable
models *are* the solutions to your problem.)

At the other extreme, `p :- not p.` has **no** stable model: assume p
false and the rule derives it; assume p true and nothing supports it. A
program with no stable model is genuinely, semantically paradoxical.

## Reading the verdict

Those three outcomes are the practical value of this lesson, so it is
worth stating them as a table you can act on:

| `--models` says | your program is | what to do |
|---|---|---|
| exactly one stable model | determinate | nothing. This is the goal |
| no stable model | self-contradictory | some condition reads its own outcome; break the loop |
| several stable models | underspecified | consistent, but a choice is unmade — add a tie-break |

The third row is the one people find surprising. Several models does
not mean the program is broken; it means it is *silent* about
something, and the engine has enumerated the ways that silence could be
resolved. `programs/eligibility-choice.dl` is the worked case: "only
one member of a household may claim" never says which, so a household
with two candidates yields two models, and a household with only one
candidate stays settled in both, so the ambiguity is localised rather
than contagious.

## The well-founded model

The **well-founded semantics** (Van Gelder–Ross–Schlipf, 1991) refuses to
guess. It's three-valued, every fact comes out *true*, *false*, or
*undefined*, and it always exists. For win/move it makes both `win(a)`
and `win(b)` undefined; for `p :- not p.` it makes p undefined. What it
can settle, it settles; what is genuinely circular, it names as such.

Both semantics ship in this engine, so the practical question is
**when to reach for which**, and the answer is clean once Lesson 2's
complexity vocabulary is in hand. The well-founded model always
exists, is unique, and is computable in polynomial time — so it is the
semantics for *query answering*: policies, audits, "what does this
rule set entail," where you need one dependable verdict per fact and
`undefined` is itself an answer. Stable models may not exist, may be
many, and finding them is NP-hard — which is not a defect but a
*feature budget*: their multiplicity is what lets a program's models
*be* the solutions to a combinatorial problem. That is answer set
programming's whole trade, and Lesson 0's industrial deployments —
train scheduling, product configuration — live exactly there: search
problems wearing rule clothing. Ask "what follows?", use the
well-founded model; ask "what are the possibilities?", enumerate the
stable ones.

## The café paradox

(The same knot ships in benefits vocabulary as
`programs/eligibility-paradox.dl` — a household stops qualifying once a
member claims — and both are the barber paradox underneath. What the
café adds is not legibility but **bystanders**: the barber's village
has one villager, while the café has Alan, Alice and Carol, whose
meals stay settled while exactly Bob's facts go undefined. That is
what makes "the paradox is localised" *visible*, and it is the
property the three-encoding table below depends on.)

Now the café paradox itself. A town's policy: anyone who does **not**
live in a household that cooks its own meals may eat free in the café.
The café is operated by one of the households, and Bob — a member of
that household — is assigned to cook the café's meals. Where will Bob
take his meals?

Encode "a household cooks its own meals" as being about the meals its
members actually eat (`programs/cafe-paradox.dl`), and you get a cycle:
Bob eats in the café iff his household doesn't cook, but his household
cooks — its meals are cooked by its own member, Bob — iff Bob eats in the
café. The engine rejects it syntactically, and `--models` delivers the
semantic verdict:

```
Stable models: none — no consistent two-valued model exists.
Well-founded model (three-valued):
  true:      eats_at_home(alan).  eats_at_home(alice).
             eats_in_cafe(carol).  household_cooks(house_a).
  undefined: eats_at_home(bob).  eats_in_cafe(bob).  household_cooks(cafe_house).
```

This is the barber paradox in catering form: the ground core is
`p :- not p` stretched over two atoms, and the well-founded model is
wonderfully precise about it: everyone else's meals are settled, and
exactly Bob's three facts are undefined. *Where will Bob take his meals?
Undefined.*

Two further encodings complete the story:

- `programs/cafe-constraint.dl` — read the argument directly (Bob
  cooks the café's meals, the café is his household, therefore his
  household cooks). The program stratifies, and the paradox reappears as
  a *data-level* integrity violation naming exactly Bob:
  `violation(bob).` Modelling choices decide whether a paradox lives in
  your rules or your data.
- `programs/cafe-foodary.dl` is the resolution. The café's food is
  delivered from another town, nobody local cooks it, the cycle is gone,
  and `eats_in_cafe(bob)` holds. Change the situation, not the rule.

## The barber, and where he came from

The knot in these programs is a century and a quarter old, and its
history is worth two minutes because the fixes rhyme.

In 1901 Bertrand Russell found a contradiction at the foundations of
set theory. Naive set theory let you form the set of everything
satisfying any property — so form **R, the set of all sets that do not
contain themselves**. Does R contain itself? If it does, it doesn't;
if it doesn't, it does. Russell wrote to Gottlob Frege in June 1902,
as the second volume of Frege's life's work — arithmetic rebuilt on
exactly that kind of set formation — was in press. Frege added an
appendix acknowledging that the foundation had given way.

The **barber** is the after-dinner version Russell used to explain it
(he credited the phrasing to an acquaintance): a village barber shaves
exactly those villagers who do not shave themselves — so who shaves
the barber? Russell's own point about the barber is the one this
lesson's machinery makes precise: the barber version is *not* a
paradox. The correct conclusion is simply that **no such barber can
exist** — the job description is unsatisfiable. The set version was
the catastrophe, because naive set theory *guaranteed* R existed. A
barber can fail to exist; a guaranteed set cannot.

Both repairs stratified. Russell's theory of types put objects in
layers, a set only allowed to contain things from layers below;
Zermelo's axioms restricted set formation instead. Lesson 3's
stratification is the same instinct made computational: predicates get
layers, and a definition may negate only what lives strictly below it.
The engine's "negation in a recursive cycle" rejection is a type error
in Russell's sense.

And the engine adjudicates Russell's distinction mechanically:

```
$ python3 datalog.py --models programs/barber.dl
Syntactic check: not stratifiable (shaves --not--> shaves).
  (Syntactic only — an unstratifiable program may still have stable models.)
Stable models: none — no consistent two-valued model exists.
Well-founded model (three-valued):
  true:      shaves(barber, plato).
  undefined: shaves(barber, barber).
```

"No stable model" *is* "no such barber exists" — the same verdict
Russell gave, computed. The well-founded model is the refinement he
didn't have: quarantine the one self-referential atom and keep the
rest of the village's facts, so `shaves(barber, plato)` stays simply
true. The café paradox is this knot in catering dress, the eligibility
paradox is it in benefits dress — one structure, many costumes, which
is why Lesson 0 warns that language models have seen every costume.

## The moral

Three programs, one story, three verdicts:

| Encoding | Syntactic | Semantic |
|---|---|---|
| self-referential | rejected | no stable model; Bob undefined in the well-founded model |
| direct | stratifies | model exists; `violation(bob)` |
| Foodary | stratifies | model exists; Bob eats free |

A sensible-sounding policy can be formally paradoxical, the paradox can
be localized to a single individual, and whether it shows up as "no
model" or "constraint violated" is a modelling choice. A reasoning system
worth trusting detects all of this rather than silently picking an
answer.


## Under the hood: `semantics.py` in three functions

**`semantics.py` is two short functions and two one-liners** once you
see the shape:
`ground_program` instantiates rules over an envelope (the least model
with all negations granted — provably a superset of every stable model,
which is what makes exhaustive search sound), `_gamma` is the
Gelfond–Lifschitz operator (delete rules whose negated atoms are in the
candidate; forward-chain the rest), and both semantics are one-liners
over it: stable = "Γ(M) == M", well-founded = the least fixpoint of Γ∘Γ
with the undefined zone read off the gap.

That exhaustive search is the teaching simplification: clingo, the
industrial stable-model engine, finds models by conflict-driven
learning instead of enumeration.

## Exercises

1. The lesson gave away the barber's verdict, so earn it back: change
   the *village* (facts only — the rule stays) so that a stable model
   exists. Two different one-line repairs work; find both, and say
   what each corresponds to in Russell's terms.
2. Give win/move an acyclic move graph (a chain). How many stable models
   now? What does that say about where the ambiguity came from?
3. Invent a third reading of the café: make `household_cooks` an EDB
   fact you assert or don't. What happens in each case?
4. A colleague sees `eligibility-choice.dl`'s two models and proposes
   storing "eligible(bob) ∨ eligible(cyril)" as a *disjunctive fact*
   and teaching the engine to reason over it. The alternative is to
   keep the models as a set and answer queries against it two ways:
   what holds in *every* model, and what holds in *some* model.
   Compute both answer sets for `eligible/1` by hand from the two
   models, and explain why the set-of-models route stays cheap per
   model while reasoning over stored disjunctions jumps a complexity
   class.

Next: [for all](06-for-all.md) — the third figure in this lesson's
gallery: after the contradictory and the ambiguous, the rejected
program that was neither, and the construction that rescues it.
