# Lesson 9 — answers

**1. `mult` forwards and backwards.**

```sh
python3 prolog.py programs/09-peano.pl -q 'mult(s(s(zero)), s(s(zero)), X)'
   X = s(s(s(s(zero))))          # 2 × 2 = 4
python3 prolog.py programs/09-peano.pl -q 'mult(X, s(s(zero)), s(s(s(s(zero)))))'
   X = s(s(zero))                # 4 ÷ 2 = 2, by running × in reverse
```

Division as reversed multiplication — unification's party trick, and
verified by the test suite.

**2. Why does ancestor behave identically under both engines?**

It is function-free and every SLD derivation for it terminates (the
recursion consumes a `parent` fact each step), so top-down enumerates
exactly the finite answer set that bottom-up computes — on the Datalog
fragment with terminating derivations, the two strategies are two
routes to the same least model. The divergence between engines only
appears when function symbols (lesson 9) or left recursion (lesson 13)
enter.

**3. Does `lt(X, zero)` fail finitely?**

Yes — no depth bound needed. Both `lt` clauses have `s(N)` as their
second argument, and `zero` unifies with neither, so resolution has
zero matching clauses and fails immediately. This is *finite failure*:
the honest kind of "no", as opposed to the depth-bound's "unproven".
The test suite asserts both the empty answer set and the
`incomplete = False` flag.
