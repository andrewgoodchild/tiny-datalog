# Lesson 12 — answers

Runnable ontology (exercises 1 and 4): `exercises/12-answers.dl`.

**1. Predict grandmother's classification.**

`grandmother ⊑ mother*` — directly under mother (woman ∧ ∃has_child.
parent ⊑ woman ∧ ∃has_child.person = mother, since every parent is a
person), and through mother, under woman, parent, and person. The
mirror image of grandfather ⊑ father, and the classifier finds it
unaided.

**2. Why doesn't `isa(father, tall)` make every man tall?**

`isa` states a *necessary* condition: every father is tall. Inference
flows upward from father only. Nothing says tall things are
fathers, and nothing connects man to tall at all. A `define(father,
and(man, tall, ...))` would be different: definitions are necessary
AND sufficient, so any concept provably man-and-tall-with-a-child would
then classify *under* father. Primitive vs defined is the whole game in
KL-ONE: only definitions let the classifier discover.

**3. Goal-directed subsumption via `--emit` + magic.**

```sh
python3 subsumption.py --emit programs/family-ontology.dl > /tmp/ont.dl
python3 datalog.py --magic --trace -q 'subs(grandfather, parent)' /tmp/ont.dl
```

The magic facts that appear are `magic#subs#bb(grandfather, parent)`
and the subgoals demand discovers from it: the classifier's work
narrowed to one subsumption question. (Tabling the same query shows the
same sets as tables: lesson 15's punchline, in ontology form.)

**4. A discovered equivalence.**

`exercises/12-answers.dl` defines `dad` as "a person who is a man with
a child who is a person" — syntactically different from father,
semantically identical, and the classifier prints `dad ≡ father`.
Equivalence discovery is just subsumption run both ways.

**5. The café menu as a TBox.**

The translatable part:

```prolog
isa(dish, item).
isa(drink, item).
disjoint(dish, drink).
define(garnished, and(dish, some(topped_with, herb))).
define(smoothie, and(drink, some(made_from, fruit))).
define(house_special, and(dish, some(topped_with, and(herb, some(grown_in, garden))))).
role(topped_with). role(made_from). role(grown_in).
```

One clause stays behind: *if an item lists a wine pairing...* is a
value restriction (the ∀ row) — and, tellingly, it does no
classification work here: nothing in the model is defined by its
pairing, so dropping it loses nothing, which is the question that row
tells you to ask. (*Never both* used to stay behind too; with
`disjoint/2` it is now an axiom the classifier reasons with.)

The starred discovery: **house_special ⊑ garnished**. A dish topped
with a garden-grown herb is, in particular, a dish topped with a herb
— the same one-step generalisation inside an existential as
grandfather ⊑ father. And the first minted name carries the nested
garnish: `--emit` shows `isa1(gen_3, herb)` among the inclusions —
the fresh concept for `and(herb, some(grown_in, garden))` placed
under `herb`, which is exactly the helper kind the field guide says
to stop writing by hand.

And the confused special: add `define(confused, and(dish, drink)).`
and the classifier reports `confused ⊑ ⊥ (unsatisfiable)` — the menu
item that cannot exist, caught by CR5/CR6 rather than by a customer.
