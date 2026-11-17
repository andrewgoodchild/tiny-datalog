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


## Models as solutions

The well-founded section made a promise: several stable models are
what let a program's models *be* the solutions to a search problem.
Here is the smallest honest example. Colour four regions of a map with
three colours so that no two neighbours match:

```prolog
% programs/colouring.dl
region(wa). region(nt). region(sa). region(qld).
colour(red). colour(green). colour(blue).
border(wa, nt).  border(wa, sa).  border(nt, sa).
border(nt, qld). border(sa, qld).

painted(R, C) :- region(R), colour(C), not other(R, C).
other(R, C)   :- region(R), colour(C), painted(R, D), C != D.

clash :- border(R, S), painted(R, C), painted(S, C), not clash.
```

Two idioms, and you have met both. The first pair of rules is a
**choice**: a region takes a colour unless it has taken another one,
and the two rules lean on each other through `not`, exactly as
`eligibility-choice.dl` did. Each way of settling them is a model, so
there is one model per way of painting the map.

The last rule is a **test**, and it is the barber on purpose. Where
two neighbours share a colour it says `clash` holds exactly if it does
not, and a set of facts containing that knot cannot be a model. The
paradox this lesson spent four sections diagnosing is, used
deliberately, a filter: it deletes the models you do not want.

```
$ python3 datalog.py --models -q 'painted(R, C)' programs/colouring.dl
Syntactic check: not stratifiable (clash --not--> clash).
  (Syntactic only — an unstratifiable program may still have stable models.)
Stable models: 6
  model 1: painted(nt, red).  painted(qld, green).  painted(sa, blue).  painted(wa, green).
  model 2: painted(nt, red).  painted(qld, blue).  painted(sa, green).  painted(wa, blue).
  model 3: painted(nt, green).  painted(qld, red).  painted(sa, blue).  painted(wa, red).
  model 4: painted(nt, green).  painted(qld, blue).  painted(sa, red).  painted(wa, blue).
  model 5: painted(nt, blue).  painted(qld, red).  painted(sa, green).  painted(wa, red).
  model 6: painted(nt, blue).  painted(qld, green).  painted(sa, red).  painted(wa, green).
```

Six colourings, which is every one there is. Nothing in the program
says how to search. (`-q` only chooses which atoms of each model to
print; the models are the same.)

## Finding the models: propose, check, learn

The definition of a stable model is a *check*. Hand it a set M and it
says yes or no. It does not say where to look.

The obvious search is to try every subset of the atoms that could
possibly be true. That is the definition run as written, the library
still offers it (`stable_models(..., exhaustive=True)`), and it is
hopeless: the map has 25 such atoms, so 2²⁵ candidate sets, about
thirty-three million, to find six. One more region doubles it six
times over.

What `--models` does instead is hand the guessing to something built
for guessing, and keep the definition as the judge. Three steps.

**Say what any model must look like, as yes/no constraints.** One
variable per atom, true or false. Two kinds of constraint are certain.
*Every rule holds*: if a rule's body is true, so is its head. And
*every true atom has a reason*: at least one rule for it has a true
body. A set satisfying both is called a **supported** model. Every
stable model is supported, so nothing is lost, and almost all of those
thirty-three million sets are not.

**Let a SAT solver propose one.** Finding an assignment that satisfies
a pile of yes/no constraints is the most studied search problem there
is. The solver here is forty lines (`tiny_datalog/sat.py`; lesson 26
reads it line by line), and it knows nothing about Datalog.

**Check the proposal with the definition.** Simplify every `not`
against it, forward-chain what is left, and see whether the same set
comes back. If it does, that is a stable model: record it and ask for
another. On the map that is the whole story:

```
$ python3 datalog.py --models --trace -q 'painted(R, C)' programs/colouring.dl
...
Search: 25 candidate atoms, 6 candidate models proposed
  1: stable
  2: stable
  3: stable
  4: stable
  5: stable
  6: stable
Stable models: 6
...
```

Six proposals, six models, and then the solver reports that nothing
else satisfies the constraints.

So when is a supported model *not* stable? When its reasons go round
in a circle.

```prolog
% programs/vouching.dl
person(ann). person(bob).
invited(ann).
vouches(ann, bob). vouches(bob, ann).

active(P)  :- invited(P), not revoked(P).      % a choice: is the
revoked(P) :- invited(P), not active(P).       % invitation still good?

trusted(P) :- active(P).
trusted(P) :- vouches(Q, P), trusted(Q).

breach :- person(P), not trusted(P), not breach.   % a test: all trusted
```

```
$ python3 datalog.py --models --trace programs/vouching.dl
Syntactic check: not stratifiable (active --not--> revoked --not--> active).
  (Syntactic only — an unstratifiable program may still have stable models.)
Search: 5 candidate atoms, 2 candidate models proposed
  1: refused: only each other to support trusted(ann), trusted(bob)
  2: stable
Stable models: 1
  model 1: active(ann).  trusted(ann).  trusted(bob).
```

The first proposal was: Ann's invitation is revoked, and Ann and Bob
are both trusted. Go through the constraints. Every rule holds. Every
true atom has a reason: Ann is trusted because Bob vouches for her
and Bob is trusted; Bob is trusted because Ann vouches for him and Ann
is trusted. It is a supported model, and it is nonsense.

The definition catches it. With the invitation revoked, `active(ann)`
is gone, and forward chaining from the facts never reaches
`trusted(ann)` or `trusted(bob)`: each needs the other first. This is
Lesson 2's least fixpoint doing the job it was chosen for. A
derivation has to *start* somewhere, and "true because of each other"
starts nowhere. The atoms that failed to come back are called an
**unfounded set**.

The refusal is then turned into a constraint, and this is the step
that makes the search more than trial and error. Not "never this
proposal", which would rule out one set. Instead: *Ann or Bob may be
trusted only if some rule for one of them has a true body that does
not itself rely on the other.* There is one such rule,
`trusted(ann) :- active(ann)`. So the solver now knows that trust
needs an active invitation, proposes exactly that, and the check
passes. Every later proposal resting on the same circle is ruled out
before it is made. (The constraint is called a *loop formula*; the
method is Lin and Zhao's, 2004.)

The map never needed this step, and that is not luck. Its rules have
no recursion through positive literals, so nothing can hold itself
up, and for such programs supported and stable are the same thing.

Two limits, as usual. The program is still grounded in full before
any of this starts, so the size of the grounding is the real ceiling.
And the solver is the textbook one: an industrial system such as
clingo learns a constraint from every dead end *inside* the solver
too, and works over millions of atoms. `--models` stops after 256
models, since a program with that many is asking a question other
than "list them".

The loop itself, propose, check, and turn each failure into a
constraint that rules out many candidates at once, comes back in
Lesson 26, with rules where this has atoms and provenance where this
has unfounded sets.


## Under the hood: `semantics.py` in three functions

**`semantics.py` is two short functions and two one-liners** once you
see the shape:
`ground_program` instantiates rules over an envelope (the least model
with all negations granted — provably a superset of every stable model,
which is what makes searching inside it sound), `_gamma` is the
Gelfond–Lifschitz operator (delete rules whose negated atoms are in the
candidate; forward-chain the rest), and both semantics are one-liners
over it: stable = "Γ(M) == M", well-founded = the least fixpoint of Γ∘Γ
with the undefined zone read off the gap.

The search adds two more. `_completion` writes the ground program as
clauses: a variable per atom and one per rule body, "the rule holds",
and "a true atom has a true body". `_search` is the loop: `solve`
proposes, `_gamma` checks, and a refusal becomes the clauses for its
unfounded set. A stable model, once found, is fenced off with one
clause saying "not all of these again", which is enough because no
stable model contains another. The exhaustive search is still there
behind `exhaustive=True`, and the test suite holds the two to the same
answers on random programs.

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

5. `programs/colouring.dl` has six models. Predict the number after
   `--assume 'region(tas).'`, an island with no borders, and after
   `--assume 'border(wa, qld).'` instead. Run both with `--trace`. In
   the second, how many candidate models does the search propose, and
   what does that tell you about where the work was done?
6. In `programs/vouching.dl` the circular proposal was refused and a
   model was found anyway. Withdraw the invitation
   (`--assume 'invited(ann)~.'`) and predict the verdict. Then say, in
   the terms of the "Reading the verdict" table, what kind of rule set
   this now is, and why the vouching rule cannot rescue it.

Next: [for all](06-for-all.md) — the third figure in this lesson's
gallery: after the contradictory and the ambiguous, the rejected
program that was neither, and the construction that rescues it.
