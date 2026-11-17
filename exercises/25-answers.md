# Lesson 25 — answers

Runnable examples: `exercises/25-sibling.examples` (exercise 2) and
`exercises/25-noisy.examples` (exercise 4), both over
`programs/kinship.dl`.

**1. The gain of `parent(X, Y)`.**

Before: 17 positive bindings of 81, so "positive" costs
-log2(17 / 81) = 2.25 bits. After: 8 of 8, which costs nothing. All 8
surviving bindings are old positive ones, so

    gain = 8 × (2.25 − 0) = 18.02

as the trace says. Compare `parent(X, Z)` on the line below it: it
keeps all 17 positives and scores less, 16.82, because it removes too
few negatives. Purity beat coverage here, by a little.

**2. Siblings.**

```sh
$ python3 foil.py programs/kinship.dl --examples exercises/25-sibling.examples
   + sibling(Y, X)            gain  22.53   6+ 0-
   sibling(X, Y) :- sibling(Y, X).   covers 6
warning: sibling can never hold: every rule for it needs sibling first (no base case?)
run for real: 0 of 6 positive examples derived, 0 of 75 negative
```

The same trap as same-generation: siblinghood is symmetric, so the
rule is true of every example, and it derives nothing.

The rule wanted is
`sibling(X, Y) :- parent(P, X), parent(P, Y), X != Y.` and this FOIL
cannot build it, for a reason that has nothing to do with greed:
`candidates` offers predicates and their negations, never a
comparison. Without `X != Y`, the body `parent(P, X), parent(P, Y)`
covers every person with a parent paired with themselves, which is
eight negative examples (lesson 1's own sibling bug). A learner can
only find rules its search space contains. Choosing that space is
called the **language bias**, and it is the main thing a person
contributes to rule learning.

**3. The two restrictions on `not`.**

Bound variables only: lesson 3's safety condition. `not parent(X, Z)`
with Z appearing nowhere else would ask about every Z there could be.

Never the target: lesson 3's stratification. Allowing it would let
FOIL write

```prolog
sg(X, Y) :- parent(P, X), parent(P, Y), not sg(Y, X).
```

which is recursion through negation: `sg` cannot be finished before it
is negated. The engine refuses the program, and lesson 5 is about what
it would mean if it did not.

**4. One false example.**

```sh
$ python3 foil.py programs/kinship.dl --examples exercises/25-noisy.examples
   + ancestor(Z, Y)           gain  15.35   9+ 1-
   + parent(U, Y)             gain   1.37   9+ 0-
   ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y), parent(U, Y).   covers 9
   ...
   no literal separates what is left: giving up
run for real: 17 of 18 positive examples derived, 0 of 63 negative
```

The recursive rule is damaged: it gains a third literal that means
nothing. The trace shows why. With clean examples `ancestor(Z, Y)`
left `9+ 0-`. Now it leaves `9+ 1-`: because `ancestor(gus, ada)` is
on the positive list, the lookup tells FOIL that Gus's parent Dov is
an ancestor of Ada too, which is a negative example. FOIL adds
`parent(U, Y)` (Y has a parent, which Ada does not) purely to exclude
it. Then it tries to cover the false example with a rule of its own
and gives up.

The signature of noise is a nearly pure literal followed by a patch
that removes one or two bindings, and a final rule that covers one
example. FOIL's description-length test stops there: a rule that long
to explain one example costs more than listing the example.

**5. Specialising is containment.**

```sh
$ python3 containment.py --contains 'grandparent(X, Y) :- parent(X, Z), parent(U, Y).' 'grandparent(X, Y) :- parent(X, Z), parent(Z, Y).'
=> outer contains inner, on every database
```

The homomorphism sends X, Y and Z to themselves and U to Z: "Y has
some parent" is satisfied by the particular parent the learned rule
names.

The `ancestor` rules are a different matter. `containment.py` will
compare two recursive rules, but only as single conjunctive queries,
with `ancestor` in the body treated as an arbitrary relation:

```sh
$ python3 containment.py --contains 'ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).' 'ancestor(X, Y) :- ancestor(X, Z), parent(Z, Y).'
=> neither contains the other
```

As *programs*, each with the base case, the two define the same
relation. Showing that needs an argument about the recursion, and
equivalence of recursive programs is undecidable in general (lesson
16, "Where the theory stops"). So a learned recursive rule set cannot
be checked against a textbook one by proof. It can be checked on
data, which is lesson 27.
