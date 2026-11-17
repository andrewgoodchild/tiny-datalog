# Lesson 5 — answers

**1. Repairing the village.**

Two one-line repairs, verified with `--models`:

- **Assert `shaves(barber, barber).`** Now the rule instance for the
  barber has a false premise (`not shaves(barber, barber)`), so it
  never fires for him — but the fact holds anyway, and the unique
  stable model is {shaves(barber, barber), shaves(barber, plato)}. In
  Russell's terms: the job description quietly weakened from "exactly
  those" to "at least those" — a barber who also shaves himself is no
  contradiction, only a failure of the advertised *only*.
- **Delete `person(barber).`** The rule now ranges over plato alone;
  the unique stable model is {shaves(barber, plato)}. This is the
  classic resolution of the puzzle: *no such barber exists in the
  village* — he shaves the villagers but is not one of them, so the
  description never applies to him.

Both repairs break the self-reference by changing the *world*, not the
rule — which is the honest lesson: the rule was never wrong, it was
unsatisfiable over that village.

**2. win/move on an acyclic chain a→b→c→d.**

Exactly **one** stable model: `{win(a), win(c)}`. d has no moves
(loses), so c wins; b's only move reaches a winner (b loses), so a
wins. The two-models ambiguity of the cyclic version came entirely
from the cycle — acyclic game trees have determined outcomes, and the
stable semantics computes precisely the game-theoretic answer.

**3. A third café reading: `household_cooks` as an EDB fact.**

Assert `household_cooks(cafe_house).` as data (deleting the rules that
derive it) and the program is trivially stratified: Bob eats at home.
Omit it and Bob eats free in the café. Both worlds are consistent —
because *you* decided the contested fact instead of letting the rules
decide it circularly. That is the third way out of a paradox: don't
define the fixed point, assert it. (Compare: the constraint reading
`programs/cafe-constraint.dl` derives it from who cooks; the
paradox reading lets it depend on who eats. Modelling choices, three
of them, three different formal fates.)

**4. Disjunction is an answer, not a fact to reason over.**

From the two models — {bob, edith} eligible in one, {cyril, edith} in
the other:

- holds in **every** model (the *cautious* answers): `eligible(edith)`
  only. This is what you can act on unconditionally.
- holds in **some** model (the *brave* answers): bob, cyril, edith.
  This is the space the tie-break rule will choose from.

Both are computed by enumerating models and taking an intersection or
a union — each model individually is an ordinary polynomial-time
least-model computation, and the aggregation over them is trivial. The
colleague's route makes the disjunction a *first-class formula inside
the language* (disjunctive Datalog), and evaluation must then case-split
during derivation rather than after it — the complexity of the
reasoning itself jumps a class. Same information, two homes: as an
answer-set it is cheap and honest; as a stored fact it makes every
downstream inference pay for the ambiguity. ASP systems ship the first
design, and this exercise is why.

**5. More regions, and one border too many.**

An island with no borders can take any of the three colours whatever
the mainland does, so 6 × 3 = 18 models, and the trace shows 18
proposals, every one stable.

`border(wa, qld)` makes all four regions border each other, and four
mutually adjacent regions cannot be painted with three colours:

```sh
$ python3 datalog.py --models --trace --assume 'border(wa, qld).' programs/colouring.dl
Search: 25 candidate atoms, 0 candidate models proposed
Stable models: none — no consistent two-valued model exists.
```

Zero proposals. The solver showed that the constraints cannot all be
satisfied without ever producing a candidate for the definition to
check. All the work was in the SAT search, and that is where it
usually is: the check costs one forward-chaining pass per proposal,
while ruling out thirty-three million sets is the solver's job.

**6. Nobody invited.**

```sh
$ python3 datalog.py --models --trace --assume 'invited(ann)~.' programs/vouching.dl
Search: 1 candidate atom, 0 candidate models proposed
Stable models: none — no consistent two-valued model exists.
```

No stable model: the rule set is *self-contradictory*, the second row
of the table. The policy demands that Ann and Bob be trusted, and the
only support either has is the other. Notice that `trusted(ann)` is
not even a candidate atom now: the envelope `ground_program` builds
is itself a least model, so an atom with only circular support never
gets in. What is left is `breach`, which holds exactly if it does not.

The vouching rule cannot rescue it for the reason the lesson's trace
gave. Mutual vouching satisfies every rule and gives every atom a
reason, and it still derives nothing from the facts. A test that every
person be trusted, plus rules that can only pass trust along, is a
contradiction until somebody is trusted for a reason of their own.
