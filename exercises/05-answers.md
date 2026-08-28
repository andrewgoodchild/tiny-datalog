# Lesson 5 — answers

**1. `--models` on the barber (`programs/barber.dl`).**

Undefined: exactly `shaves(barber, barber)`, the self-referential
atom. True *despite the paradox*: `shaves(barber, plato)` (plato
doesn't shave himself, so the barber definitely shaves him). The
well-founded model quarantines the paradox to the one atom that
embodies it; note also that the program has **no stable model at all** —
two-valued semantics cannot contain the damage the way three-valued
semantics can.

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
