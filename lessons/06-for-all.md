# Lesson 6 — For all, in a language that only has there-exists

A Datalog rule body is a chain of *and*-ed existentials: "there is a
member, there is a pension, there is no employment record." Nowhere in
the language is there a way to say **for all** — and sooner or later
every real rule set needs one. *Every* field must match. *Every*
dependency must be satisfied. *Every* leg of the journey must be
booked.

This lesson is about the standard move that gets you universals anyway,
why the obvious attempt is rejected by the engine, and a bonus nobody
asks for but everyone eventually needs: the same move makes recursion
through negation come out *right* on cyclic data.

## The easy case first

When the universal is not tangled in recursion, the move is three
lines, and Lesson 3 already made it a habit: **derive the
counterexample, then negate it.** "A supplier all of whose parts
passed inspection":

```prolog
bad_supplier(S)  :- supplies(S, P), not passed(P).
good_supplier(S) :- supplier(S), not bad_supplier(S).
```

"For all parts, passed" becomes "there is no part that failed" — ∀ is
¬∃¬, and both negations are the closed-world `not` of Lesson 3. This
stratifies (each `not` points at a finished relation below) and it is
the whole story — *until the universal has to recurse.*

## The hard case: every field, at every depth

Take subtyping of record types, streams included:

```prolog
field(stream, val, int).  field(stream, next, stream).
field(rich, val, int).    field(rich, meta, str).  field(rich, next, rich).
```

`S` is a subtype of `T` when **every** field of `T` appears on `S`
with a subtype-compatible type — a universal, whose inner test is the
relation being defined. Write it the obvious way, ∀ as ¬∃¬ again:

```prolog
sub(S, T) :- type(S), type(T), not badpair(S, T).
badpair(S, T) :- field(T, F, Tp), field(S, F, Sp), not sub(Sp, Tp).
```

```
REJECTED: program is not stratifiable — negation occurs inside a recursive
cycle: badpair --not--> sub --not--> badpair.
```

It *looks* like Lesson 5's territory — paradox or choice. It is
neither. The condition is perfectly meaningful; the encoding just
threaded a negation through its own recursion. This is the third
figure in the gallery Lesson 5 opened: after the genuinely
contradictory and the genuinely ambiguous, **the false alarm** — a
legitimate universal wearing a paradox's clothes.

## The fix: push the negation to the leaves

Instead of defining `sub` and negating it inside, define the
*complement* as its own positive recursion, and negate once, at the
top. What is a counterexample to "S subtypes T"? A **finite chain of
disagreement**: a field of T that S lacks, or a primitive mismatch, or
a field whose types disagree — recursively:

```prolog
nsub(S, T) :- prim(S), prim(T), distinct(S, T).
nsub(S, T) :- type(S), field(T, F, _), not hasfield(S, F).
nsub(S, T) :- field(T, F, Tp), field(S, F, Sp), nsub(Sp, Tp).

sub(S, T) :- type(S), type(T), not nsub(S, T).
```

The recursion in `nsub` is **positive** — no negation rides through
it — and the two `not`s point at finished lower strata. Three strata,
engine satisfied, and `programs/record-subtyping.dl` is the full
version:

```
$ python3 datalog.py -q 'sub(rich, stream)' programs/record-subtyping.dl
?- sub(rich, stream)
   sub(rich, stream).
   (1 answer)
```

**Habit** (Lesson 17 collects these): when you want "for all", derive
"there is a counterexample" as a positive relation, and negate it one
stratum up.

## The bonus: cycles come out right

Look at what just happened on the recursive types. `stream`'s `next`
field is `stream` itself; deciding `sub(rich, stream)` chases into
`nsub(rich, stream)` — its own question. As a *positive least
fixpoint*, `nsub` answers by well-founded derivation: no finite chain
of disagreement exists, so `nsub(rich, stream)` is never derived, so
`sub(rich, stream)` holds. The subtype relation on cyclic structures
is **coinductive** — true by unfalsifiability rather than by finite
proof — and the complement construction computes exactly that:
deriving the failure inductively and taking success as its absence
*is* the greatest fixpoint, obtained as the negation of a least one.
(Lesson 18 gives that slogan its categorical name.)

Mutual recursion rides along free — `ping` and `pong` point at each
other, and both subtype `stream`. And when subtyping genuinely fails,
the counterexample is a real derivation with a real explanation:

```
$ python3 datalog.py --explain 'nsub(brok, stream)' programs/record-subtyping.dl
?- explain nsub(brok, stream)
   nsub(brok, stream)   [via nsub(S, T) :- field(T, F, Tp), field(S, F, Sp), nsub(Sp, Tp).]
     field(stream, val, int)   (base fact)
     field(brok, val, str)   (base fact)
     nsub(str, int)   [via nsub(S, T) :- prim(S), prim(T), distinct(S, T).]
       prim(str)   (base fact)
       prim(int)   (base fact)
       distinct(str, int)   (base fact)
```

Failure has a proof; success is the checked absence of one. That
asymmetry is not an accident — it is what "coinductive" means,
operationally.

## The same shape elsewhere

Once you can see it, this pattern is everywhere the course goes next.
Lesson 12's classifier is its mirror image: the EL completion rules
derive `subs` positively from the *existential* side, where this
lesson derived `nsub` positively from the *universal* side — two
saturations, one for ∃, one for ¬∀. And a symptom worth remembering:
**if you find yourself banning cycles so your checker terminates, you
are probably running this lesson's computation top-down.** The
bottom-up complement needs no such ban — the cycles above are not
merely tolerated, they are decided correctly.

One warning before the exercises make it concrete: the construction
always computes the *greatest* fixpoint reading of the universal, and
not every domain wants that. Whether "everything on the cycle counts
as succeeding" is a feature (subtyping, bisimulation) or a bug (build
systems, where a dependency cycle should *fail*) is a fact about your
domain, not your encoding — exercise 4 walks into the trap
deliberately.

## Exercises

1. Add `field(lazy, val, int). field(lazy, next, brok).` and predict
   `sub(lazy, stream)` before running it. Where does the chain of
   disagreement bottom out?
2. `sub(rich, stream)` holds but `sub(stream, rich)` does not. State
   the general principle in one sentence, and say why it is the same
   principle as "a subclass may add methods."
3. Run `--models` on the rejected version (two types suffice:
   `stream` and `int`). It has exactly two stable models. Identify
   which fixpoint each one is, and which one the complement
   construction chose.
4. Build systems want the *other* fixpoint: a package is buildable
   only if every dependency is, and a dependency **cycle should mean
   failure**, not success. Write the naive rules for a three-package
   cycle, run `--models`, and explain what the well-founded model's
   `undefined` is honestly telling you. Then say which single extra
   fact-per-package repairs the modelling (Lesson 4 taught the move).

Next: [magic sets](07-magic-sets.md) — asking questions efficiently.
