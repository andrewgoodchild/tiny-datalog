# Lesson 7 — Probabilistic Datalog, honestly

> **Follows on from lesson 6.** Assumes you have met semirings.

Give facts probabilities and you have the on-ramp to neurosymbolic AI:
a neural network estimates fact confidences, a logic program reasons over
them. This lesson builds the piece of that which is *actually a
semiring* — and shows precisely where the simple story breaks, because
the breakage is the interesting part.

## Viterbi: the probability of the best derivation

`programs/07-prob-reach.dl` is a flaky network:

```prolog
link(s, a) @ 0.9.    link(a, t) @ 0.9.
link(s, b) @ 0.5.    link(b, t) @ 0.95.
link(a, b) @ 0.8.
reach(X, Y) :- link(X, Y).
reach(X, Z) :- link(X, Y), reach(Y, Z).
```

```sh
$ python3 semiring.py --semiring viterbi -q 'reach(s, t)' programs/07-prob-reach.dl
   reach(s, t) = 0.81
```

The **Viterbi semiring** (max, x) scores each fact with the probability
of its most likely single derivation: route s-a-t gives 0.9 x 0.9 = 0.81,
which beats s-b-t (0.475) and s-a-b-t (0.684). Max is idempotent, so the
fixpoint converges even on cyclic graphs (going around a loop only
multiplies in more ≤1 factors).

## Why "just add up the routes" is not available

The value you probably wanted is the *total* probability that s reaches t
— some route works. For independent events the natural combination is
`plus(a, b) = a + b - ab` (noisy-or) with `times(a, b) = ab`. Check
distributivity, which semirings require:

```
a x (b + c - bc)         = ab + ac - abc
(a x b) + (a x c) - (ab)(ac) = ab + ac - a²bc
```

Not equal. **Noisy-or times product is not a semiring**, and the failure
isn't pedantry — it's the correlation problem wearing algebraic clothes.
Routes s-a-t and s-a-b-t share the link s-a; treating their probabilities
as independent double-counts it. No per-fact bookkeeping can fix this,
because the answer genuinely depends on *which sets of links* each route
uses.

But we already have machinery for "which sets of facts support this" —
why-provenance, from Lesson 6. That is exactly how real systems do it:
**Scallop** (PLDI 2023) evaluates over provenance semirings (typically
top-k proofs) and only then converts evidence sets to probabilities by
weighted model counting; because the provenance values are differentiable
functions of the input probabilities, the whole pipeline can sit inside a
neural network and be trained end-to-end.

So the honest summary:

So what *is* the total probability? You compute it from the witness
sets, not from a semiring. `exercises/06-homomorphism.py`'s companion
does exactly that — enumerate the 2⁵ worlds, keep the ones where s
reaches t, sum their probabilities:

```
$ python3 exercises/07-exact-prob.py
exact P(s reaches t)  = 0.934450   (enumeration over 32 worlds)
Viterbi (best route)  = 0.810000
exact >= Viterbi: True
```

The exact answer must be at least the Viterbi one, because "some route
works" includes "the best route works". The 0.12 gap is the value of
the backup paths — precisely the redundancy a single-derivation
semiring cannot see.

That enumeration is exponential, which is why real systems compute it
from *provenance* rather than from possible worlds: get the witness
sets once (lesson 6), then hand them to a weighted model counter. That
is the architecture Scallop uses, and the reason its provenance is
differentiable is what lets the whole pipeline sit inside a neural
network.

| Question | Tool | Status here |
|---|---|---|
| probability of the best derivation | Viterbi semiring | implemented |
| total probability of derivability | witness sets + model counting | worked above |


## Exercises

1. By hand, list all routes s to t and their probabilities; verify the
   Viterbi answers for `reach(s, t)` and `reach(s, b)`.
2. Drop `link(s, a)` to 0.6. Which route is most likely now? Verify.
3. Combine the two semirings: get the witness sets for `reach(s, t)` from
   `--semiring why`, then compute the exact total probability by
   inclusion–exclusion over those sets (each link up independently with
   its `@` probability). Compare with the Viterbi number — why must the
   exact answer always be at least as large?

Next: [incremental maintenance](08-incremental.md) — repairing answers
when the facts change.
