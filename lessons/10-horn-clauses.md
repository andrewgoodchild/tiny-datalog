# Lesson 10 — Horn clauses: the boundary Datalog lives on

Every rule in this repository is a **Horn clause**: a formula with at
most one positive literal, `b₁ ∧ … ∧ bₙ → h`. Datalog is Horn-clause
logic with one thing confiscated: **function symbols**. This lesson
gives them back, to show exactly what the confiscation bought.

## Who was Horn?

**Alfred Horn** (1918–2001), a mathematician at UCLA — and the origin
of the name is one of the field's best ironies. His 1951 paper *"On
sentences which are true of direct unions of algebras"* singled out
this clause shape for a reason that had nothing to do with
computation: sentences of this form are preserved when you take direct
products of algebraic structures. Pure model theory, no machines in
sight.

Twenty years later, Kowalski, Colmerauer and van Emden discovered that
the very same fragment is the one where proof search is tractable and
every program has a least model — the properties this whole course
runs on — and the name stuck. Horn identified the clauses; he never
knew what they would become. It is a recurring pattern in this field:
the fragment chosen for one good property turns out to have been
chosen for all of them (Lesson 15 meets it again when a 1977
containment theorem turns out to be the theory of 2020s query
optimisers).

## The boundary, stated by the engine

`programs/peano.pl` defines arithmetic the logician's way:

```prolog
nat(zero).
nat(s(N)) :- nat(N).
add(zero, N, N).
add(s(M), N, s(R)) :- add(M, N, R).
```

Feed it to the Datalog engine:

```sh
$ python3 datalog.py programs/peano.pl
error: function symbols are not Datalog: term s(N) in nat(s(N)) :- nat(N).
Datalog bans compound terms so that bottom-up evaluation always
terminates; for Horn clauses with function symbols use the top-down
engine (prolog.py).
```

The refusal is the lesson. With `s(...)` admitted, the set of possible
facts is infinite — `nat(zero)`, `nat(s(zero))`, `nat(s(s(zero)))`, … —
and bottom-up evaluation would enumerate it forever. Datalog's guarantee
that *every program terminates* is bought entirely by this ban. One
syntax rule separates a query language from a programming language.

## The other side: SLD resolution

SLD stands for *Selective Linear resolution for Definite clauses*, and
it is the proof procedure Prolog runs on.

`prolog.py` is a miniature top-down interpreter: to prove a goal, find a
clause whose head **unifies** with it, and recursively prove that
clause's body. This is SLD resolution: the heart of Prolog.

The deep idea is that every clause supports **two readings at once**.
Declaratively, `add(s(X), Y, s(Z)) :- add(X, Y, Z).` is a timeless
implication — *if* the body holds, the head holds. Procedurally, it is
an instruction: *to prove* the head, work through the clauses top to
bottom, unify, and prove the body left to right. Prolog is the
discovery that one text can be both, and the discipline of logic
programming is writing clauses whose two readings agree. (Bottom-up
Datalog only ever uses the declarative reading — which is why rule
order never matters in the rest of this course, and starts mattering
here.)

```sh
$ python3 prolog.py programs/peano.pl -q 'add(s(zero), s(s(zero)), X)'
?- add(s(zero), s(s(zero)), X)
   X = s(s(s(zero)))
   (1 solution)
```

Unification makes the program *reversible* — ask which pairs sum to two:

```sh
$ python3 prolog.py programs/peano.pl -q 'add(X, Y, s(s(zero)))'
   X = zero,  Y = s(s(zero))
   X = s(zero),  Y = s(zero)
   X = s(s(zero)),  Y = zero
   (3 solutions)
```

The price appears on the very next query:

```sh
$ python3 prolog.py programs/peano.pl -q 'nat(X)' --max-solutions 5
   X = zero
   X = s(zero)
   ...
   (5 solutions (more may exist: search truncated))
```

`nat(X)` has infinitely many answers; only a **depth bound** keeps the
search finite, and the interpreter is careful to say when the bound was
hit — "no more solutions" then means *unproven*, not *false*. Termination
is not a property you can get back with cleverness: whether a Horn-clause
program halts is undecidable in general.

Two deliberate differences from real Prolog: unification here includes
the **occurs check** (`X = s(X)` fails instead of silently building an
infinite term — try `eq(Y, s(Y))` against `eq(X, X).`), and there is no
cut, arithmetic, or I/O. Just resolution.

## The trade, in one table

|  | Datalog (bottom-up) | Horn clauses (top-down) |
|---|---|---|
| function symbols | banned | yes |
| termination | guaranteed | undecidable |
| all answers at once | yes (fixpoint) | enumerated, maybe forever |
| goal-directed | via magic sets (Lesson 6) | natively |
| data structures | none — facts only | lists, trees, numbers |

Magic sets (Lesson 6) is this table's punchline: it imports top-down's
goal-direction into bottom-up evaluation *without* importing the
non-termination — possible only because the function-symbol ban keeps
everything finite.

## Where this sits today

Add theory constraints (arithmetic, arrays) to Horn clauses and you get
**constrained Horn clauses**, the standard intermediate language of
modern program verification (Z3's Spacer solver, and CHC-COMP, the
annual competition for them). Different solving
technology (satisfiability modulo theories, interpolation), same clause shape you've been writing
for nine lessons.


## Exercises

1. Write `mult` queries: what is 2 x 2? Then run it backwards:
   `mult(X, s(s(zero)), s(s(s(s(zero)))))`.
2. Why does the ancestor program from Lesson 1 behave identically under
   both engines? What property of the program guarantees it?
3. `lt(X, zero)` should fail. Does it fail *finitely* here? Explain
   why the depth bound isn't needed for this one.

Next: [KL-ONE and subsumption](11-kl-one-subsumption.md) — Datalog's
*other* neighbour, and this one compiles back in.
