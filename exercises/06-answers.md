# Lesson 6 — answers

**1. `sub(lazy, stream)`?**

No. The chain of disagreement: `stream`'s `next` field is `stream`,
`lazy`'s is `brok`, so the question reduces to `nsub(brok, stream)` —
and that bottoms out at the primitive mismatch `nsub(str, int)` on the
`val` field. Three links: lazy→brok on `next`, brok→brok's own `val`,
str≠int. Run `--explain 'nsub(lazy, stream)'` and the engine prints
exactly this chain.

**2. The general principle.**

More fields make a *more specific* type, and a more specific type may
stand wherever a more general one is expected — `rich` has everything
`stream` promises (and more), so it can serve as a `stream`; `stream`
lacks `meta`, so it cannot serve as a `rich`. It is the same principle
as "a subclass may add methods": adding capabilities narrows the set
of values while widening where they are accepted. (Model-theoretically
it is Lesson 16's homomorphism direction, one level down.)

**3. The two stable models are the two fixpoints.**

```
Stable models: 2
  model 1: badpair(stream, stream).  sub(int, int).  sub(int, stream).  sub(stream, int).  ...
  model 2: sub(int, int).  sub(int, stream).  sub(stream, int).  sub(stream, stream).  ...
```

The models disagree on exactly one thing: `sub(stream, stream)`.
Model 1 is the **inductive** (least-fixpoint) reading — a stream
subtypes itself only if that can be finitely proven, and the cycle
means it never can. Model 2 is the **coinductive** (greatest-fixpoint)
reading — it holds because nothing refutes it. The well-founded model
refuses to choose and marks the atom undefined. The complement
construction chose model 2: `nsub(stream, stream)` has no finite
derivation, so `sub(stream, stream)` holds. The rejected program was
not wrong, it was *ambiguous between μ and ν* — and the engine's
"several stable models" verdict (Lesson 5) said so all along.

(The toy omits the primitive/record incompatibility rules, which is
why `sub(int, stream)` appears; the shipped program has them.)

**4. The build-system trap.**

```prolog
dep(app, libx). dep(libx, liby). dep(liby, libx).
pkg(app). pkg(libx). pkg(liby). pkg(solo).
buildable(X) :- pkg(X), not blocked(X).
blocked(X) :- dep(X, Y), not buildable(Y).
```

`--models` reports two stable models — one where the whole cycle is
blocked, one where the whole cycle is buildable — and a well-founded
model with `solo` buildable and every cycle member **undefined**. The
undefined is the honest verdict: *these rules cannot decide a cycle*,
because the rules only say "buildable unless something blocks it" and
on a cycle each package's fate rests on its own. Builds want the
inductive reading (a cycle should fail), but the complement
construction would deliver the coinductive one (a cycle would
"succeed" vacuously) — the same trick that saved subtyping betrays
builds. The repair is Lesson 4's move exactly: absence of a blocker is
not evidence of a build. Add a recorded fact per package —
`built(X)`, a ledger written by the build system itself — and derive
from the ledger, not from the absence of failure.
