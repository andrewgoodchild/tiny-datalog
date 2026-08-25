# Lesson 10 — answers

Runnable ontology (exercises 1 and 4): `exercises/10-answers.dl`.

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
same sets as tables: lesson 13's punchline, in ontology form.)

**4. A discovered equivalence.**

`exercises/10-answers.dl` defines `dad` as "a person who is a man with
a child who is a person" — syntactically different from father,
semantically identical, and the classifier prints `dad ≡ father`.
Equivalence discovery is just subsumption run both ways.
