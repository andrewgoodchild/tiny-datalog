# Lesson 24 — answers

Runnable rules: `exercises/24-answers.dl` (exercises 2 and 4, on top of
`programs/memory.dl`) and `exercises/24-product-semiring.py`
(exercise 3).

**1. The move to Globex.**

`current(user, works_at, globex)`, and only that. The Globex statement
is later than the Acme one and `works_at` is functional, so Acme is
superseded from 2024-09-01, and with `now` at 2024-10-01 that date
has passed. Note what did not happen: the Acme statement is still in
the file, and moving `now` back to 2024-08-01 brings Acme back as the
current answer. The memory can still say where the user worked in
the spring. The manager conflict from the lesson is still reported,
because nothing in the new episode settled it.

**2. Breaking ties by episode order.**

```prolog
episode(e1, 1). episode(e2, 2). episode(e3, 3).
episode(e4, 4). episode(e5, 5). episode(e6, 6).

superseded(E, R, O, F, F) :- said(E, R, O, F, Ep1), functional(R),
                             said(E, R, O2, F, Ep2), O != O2,
                             episode(Ep1, N1), episode(Ep2, N2), N1 < N2.
```

A second rule for `superseded`: two statements on the *same* date,
and the one from the earlier episode ends on that date. The head
repeats `F` because the end of validity is the day itself; writing
`U` would leave it unbound, which safety refuses. With it, Sam is
superseded by Dana, the user has one manager, and the constraint is
satisfied:

```
$ python3 datalog.py -q 'current(user, manager, M)' exercises/24-answers.dl
?- current(user, manager, M)
   current(user, manager, dana).
   (1 answer)
```

Should a memory use it? Usually not for something like this. The rule
quietly turns "the later remark in the same conversation wins" into a
belief, and that reading is wrong for "Dana, while Sam's away". It is
the same choice lesson 17 warned about: the engine can make a
contradiction *go away* by adding a priority, but only a person can
say whether the priority is true. Ties by episode order are
reasonable where the later statement is plainly a correction ("sorry,
I meant Dana"), and a good extractor can mark those by writing an
explicit correction instead of a second statement. The constraint
then has nothing to report, for the right reason.

**3. Confidence and evidence in one pass.**

```
$ python3 exercises/24-product-semiring.py
product  reports_to(user, marco) = 0.72, from {manager(dana, marco), manager(user, dana)} | {manager(sam, marco), manager(user, sam)}
best     reports_to(user, marco) = 0.72, from {manager(sam, marco), manager(user, sam)}
```

The product of two semirings, applying each operation to each half,
is always a semiring, so pairing Viterbi with why-provenance is
correct. But look at what it computes. Each half combines alternatives
on its own: the confidence is the best chain's, and the evidence is
*every* minimal witness set, including the weak chain through Dana.
The pair does not say "0.72, because of this chain". It says "0.72,
and separately, here is everything that supports it".

"The best confidence and the evidence for *that*" is a different
semiring, `Best` in the script. Its `plus` keeps whichever pair has
the higher confidence, and merges evidence only on a tie. That is a
semiring because `max` always returns one of its arguments, and
multiplying by a positive confidence never changes which of two values
is larger, so choosing first and multiplying later gives the same
result as multiplying first and choosing later. (A confidence of 0
would break this: everything ties at 0.)

Which one an assistant should report depends on the question. "Why do
you think that?" wants `Best`'s answer. "What would I have to correct
to change your mind?" wants the product's: retracting the Sam chain
alone leaves the Dana chain, at 0.3.

**4. Never suggest a dish the user is allergic to.**

```prolog
:- recommended(U, D), contains(D, I), current(U, allergy, I).
```

With the answer file's data:

```
$ python3 datalog.py exercises/24-answers.dl
...
constraint violated: :- recommended(U, D), contains(D, I), current(U, allergy, I).
   recommended(user, satay), contains(satay, peanuts), current(user, allergy, peanuts)
   (1 counterexample)
```

The constraint joins the assistant's own output with the memory, and
that is the useful shape. A constraint can check what the agent is
*about to do*, not just what it knows. Run it with `--assume` on the
suggestions before they are shown, as the lesson did for new
statements.

**5. Is an allergy functional?**

No. A person can have several allergies, and `functional` would make
each new one end the last. So, as with `knows` in lesson 23, the
statements accumulate, and nothing the user says later about a
*different* food can end one. That is the safe default for an allergy.
For one to stop being current, the user has to say something about
*that* allergy ("I've outgrown the peanut allergy"), and the extractor
has to write that down as a statement of its own, such as
`said(user, outgrew, peanuts, "2024-11-02", e12)`, with a rule that
ends the allergy from that date. The asymmetry is deliberate. Getting
"likes" wrong costs a bad suggestion, and getting an allergy wrong
costs much more, so it should take an explicit statement to end one.
