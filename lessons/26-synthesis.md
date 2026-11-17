# Lesson 26 — Finding rules by selection: provenance tells the search why

> Needs lesson 25. One section leans on lesson 8 (semirings and
> why-provenance), and says which.

Lesson 25 ended with FOIL handed a dozen examples and answering with
three rules, none recursive, one absurd. Here is the same file, handed
to a different idea:

```
$ python3 synthesis.py programs/kinship.dl --examples programs/ancestor-sparse.examples
target ancestor/2: 6 positive examples, 6 negative
40 candidate rules: bodies of up to 2 atoms, 1 extra variable
5 rounds, 7 constraints, 219 evaluations
learned 2 rules:
   ancestor(X, Y) :- parent(X, Y).
   ancestor(X, Y) :- ancestor(X, Z), ancestor(Z, Y).
run for real: 6 of 6 positive examples derived, 0 of 6 negative
```

Six pairs that are ancestors, six that are not, and it found the
recursion. The approach is ProSynth's (Raghothaman, Mendelson, Zhao,
Naik and Scholz, 2020), and it rests on two changes of mind. FOIL
*builds* rules; this *chooses* among rules already written down. And
FOIL judges a rule by looking things up in the examples; this runs the
program, on the engine, every time.

## Learning as rule selection

Write down every rule that might be in the answer. For `ancestor`,
with bodies of at most two atoms over `parent` and `ancestor`, and one
variable beyond the head's two, that is 40 rules:

```
$ python3 synthesis.py programs/kinship.dl --examples programs/ancestor-sparse.examples -t
target ancestor/2: 6 positive examples, 6 negative
40 candidate rules: bodies of up to 2 atoms, 1 extra variable
   r1   ancestor(X, Y) :- ancestor(Y, X).
   r2   ancestor(X, Y) :- parent(X, Y).
   r3   ancestor(X, Y) :- parent(Y, X).
   ...
   r5   ancestor(X, Y) :- ancestor(X, Z), ancestor(Y, Z).
   r6   ancestor(X, Y) :- ancestor(X, Z), ancestor(Z, Y).
   ...
   r40  ancestor(X, Y) :- parent(Z, X), parent(Z, Y).
round 1: try {-}: 0 wrong, 6 missing
   missing ancestor(ada, ben): require one of {r2, r3, r33, r34, r35, r36, r37, r38, r39, r40}
round 2: try {r2}: 0 wrong, 3 missing
   missing ancestor(ada, gus): require one of {r5, r6, r9, r10, r18, r20, r22, r23, r26, r27, r29, r31}
round 3: try {r2, r5}: 3 wrong, 3 missing
   wrong ancestor(ben, cat), derived by {r2, r5}: forbid that set
   missing ancestor(ada, gus): require one of {r1, r3, r6, r10, r11, r14, r15, r16, r17, r18, r21, r22, r23, r25, r26, r27, r29, r30, r31, r38, r39, r40}
round 4: try {r3, r5}: 5 wrong, 3 missing
   wrong ancestor(ben, cat), derived by {r3, r5}: forbid that set
   wrong ancestor(dov, ben), derived by {r3}: forbid that set
   missing ancestor(ada, ben): require one of {r1, r2, r11, r12, r13, r15, r17, r18, r19, r20, r23, r24, r26, r27, r28, r29, r33, r36, r37}
round 5: try {r2, r6}: 0 wrong, 0 missing
5 rounds, 7 constraints, 219 evaluations
learned 2 rules:
   ancestor(X, Y) :- parent(X, Y).
   ancestor(X, Y) :- ancestor(X, Z), ancestor(Z, Y).
run for real: 6 of 6 positive examples derived, 0 of 6 negative
```

Most of the 40 are nonsense, and that is fine. Nobody had to judge
them. A program is now a *subset* of the candidates: forty switches,
each on or off, and learning means finding a setting of the switches
whose rules derive every positive example and no negative one.

There are 2⁴⁰ settings, about a trillion. The loop above tried five.

## The loop

1. A solver proposes a subset that satisfies every constraint learned
   so far. At the start there are none, so it proposes the smallest
   subset there is: no rules.
2. The engine runs that subset as a program.
3. If the answers match the examples, stop.
4. If not, the failure is turned into a constraint that this subset
   violates, and the loop returns to 1.

This shape has a name, **counterexample-guided inductive synthesis**,
and it is only as good as step 4. A constraint that ruled out just the
one failed subset would leave a trillion minus one. The contribution
of ProSynth is that a Datalog engine can say *why* a subset failed,
and the reason rules out a large part of the space at once. There are
two kinds of failure, and each has its own kind of reason.

## Why: a wrong answer names the rules that made it

Round 3 tried `{r2, r5}` and derived `ancestor(ben, cat)`, which the
examples forbid. Ben and Cat are siblings; `r5` says two people with a
common descendant are ancestor and descendant, and `r2` supplied the
facts for it to work on.

The constraint learned is "never r2 and r5 together". Not "never this
subset": *any* subset containing both will derive `ancestor(ben, cat)`
again, because rules only add answers. A quarter of the whole space is
gone in one line.

Where does `{r2, r5}` come from? It is the wrong answer's
**why-provenance**, and this is lesson 8 put to work. There, the why
semiring carried, for each derived fact, the minimal sets of *base
facts* sufficient to derive it:

```
path(a, d) = {edge(a, b), edge(b, c), edge(c, d)} | {edge(a, b), edge(b, d)} | ...
```

Here the question is which *rules* suffice, so the tokens change and
nothing else does. Each candidate gets one extra body literal that
only it carries:

```prolog
ancestor(X, Y) :- ancestor(X, Z), ancestor(Y, Z), #rule(5).
```

and a fact `#rule(5).` when it is switched on. Then the provenance is
computed with a semiring six lines long:

```python
class RuleProvenance(WhySemiring):
    name = "rules"

    def fact_value(self, pred, tup, weight):
        return frozenset([frozenset(tup)]) if pred == TAG else self.one
```

A `#rule` fact is worth its own number. Every other fact is worth
`one`, the semiring's "nothing to report". Addition and multiplication
are inherited unchanged, so a derived fact's value is the minimal sets
of rule numbers that derive it. (Lesson 8 proved that why-provenance
cannot be turned into derivation *counts* after the fact. It can be
turned into this: setting some tokens to `one` is a semiring
homomorphism, so rule provenance is an honest shadow of the full
thing.)

A wrong answer may have several minimal sets, and each becomes a
constraint. Round 4 shows a set of size one: `r3`, "your child is your
ancestor", derives a forbidden fact all by itself, so `r3` is off for
good.

## Why not: a missing answer names the rules that could make it

Round 1 tried no rules and derived nothing, so all six positive
examples were missing. A missing answer has no derivation to inspect.
What it has is an argument from **monotonicity**: a program without
`not` only gains answers when rules are added. So if a subset fails to
derive a fact, every *smaller* subset fails too, and at least one rule
outside it must come on.

"At least one of the other 40" is true and nearly worthless. The trick
is to make the failing subset as large as possible first. Keep
switching candidates on, for as long as `ancestor(ada, ben)` stays
missing. When no more can be added, the ones still off are a short
list, and the constraint is that at least one of them is needed:

```
   missing ancestor(ada, ben): require one of {r2, r3, r33, r34, r35, r36, r37, r38, r39, r40}
```

Thirty rules were switched on without deriving the fact, and they are
all ruled out as *the* reason it is missing. (Exercise 1 asks what the
remaining ten have in common.) `why_not` adds the candidates in
halves, which is Zeller's delta debugging: a batch of thirty
irrelevant rules costs one run of the engine, not thirty.

The clause is not unique. Adding candidates in another order can
strand a different set, and both are sound. That is the usual
situation with why-not explanations, and the reason lesson 17's
why-not reports per rule: an absence has many sufficient causes.

## The solver

Every constraint is a clause over forty yes/no variables: "not r2 or
not r5", "r2 or r3 or r33 or ...". Finding an assignment that
satisfies a set of clauses is SAT, the original NP-complete problem,
and `solve` in `tiny_datalog/sat.py` is the textbook method, DPLL, in
forty lines. It has three moves:

- **Forced.** A clause with one literal left can only be satisfied
  one way, so do that. This is *unit propagation*, and it is repeated
  until nothing is forced.
- **Guess.** Otherwise pick a variable and try a value.
- **Back up.** If a clause is left with no literals at all, the last
  guess was wrong: return to it and try the other value.

Each assignment simplifies the clauses. A clause containing a literal
that just became true is satisfied and dropped. A clause containing
the opposite literal loses it, and that is how a clause shrinks
towards being forced.

### One call, by hand

By round 5 of the `ancestor` run the solver holds seven clauses. Four
are why-not clauses, long lists of rules of which one is required, and
three are why clauses:

```
1.  r2 or r3 or r33 or r34 or r35 or r36 or r37 or r38 or r39 or r40
2.  r5 or r6 or r9 or r10 or r18 or r20 or r22 or r23 or r26 or r27 or r29 or r31
3.  not r2 or not r5
4.  r1 or r3 or r6 or r10 or ...                    (22 rules)
5.  not r3 or not r5
6.  not r3
7.  r1 or r2 or r11 or r12 or ...                   (19 rules)
```

Here is everything the solver does with them:

| Move | Assignment | Why |
|---|---|---|
| forced | r3 off | clause 6 is one literal |
| guess, 8 times | r40, r39, ... r33 off | highest-numbered rule first, *off* first |
| forced | r2 on | clause 1 has nothing else left |
| forced | r5 off | clause 3, now that r2 is on |
| guess, 18 times | r31, r30, ... r9 off | as before |
| forced | r6 on | clause 2 has only r6 left |
| done | | every clause is satisfied |

The answer is `{r2, r6}`, which is round 5's proposal and the program
the loop returns. Three things in that table are worth noticing.

The guesses decided nothing. Every one of them was "off", and both
rules in the answer were *forced* on, by clauses that had run out of
alternatives. That is the "off first" habit at work: the solver
switches a rule on only when the constraints leave it no choice, so
each proposal is close to the smallest program the constraints allow,
the loop approaches the answer from below, and the wrong answers it
meets come with small provenance.

The solver never looked at ten of the forty rules. `r32` appears in
no clause, and rules such as `r12` appear only in clause 7, which `r2`
had already satisfied. A rule nothing asks for is left off without a
decision.

And it never backed up. On this problem no guess was ever wrong, which
is common when the clauses are few and mostly positive. The third move
earns its place on harder inputs: the 84-clause run on same-generation
below needs it.

One caution about "small". Off-first gives a program with few rules,
not the fewest. Which rule gets forced on depends on the order rules
are tried in, and a proposal can carry a rule that a later constraint
made unnecessary. That is why `search` ends with `_prune`, which drops
each rule whose loss the examples cannot see, and why exercise 5's
answer is "an accident of numbering".

### What the engine is to the solver

Step back from the details and the loop has a familiar outline. A SAT
solver knows nothing about Datalog. It proposes an assignment that is
consistent with the clauses it has. A second component, which knows
what the variables *mean*, checks the proposal and either accepts it
or returns a clause explaining what is wrong with it. The solver adds
the clause and proposes again.

That is the architecture of an SMT solver, where the second component
is called a **theory solver** and reasons about arithmetic, or arrays,
or bit-vectors. Here the theory is "what these rules derive from these
facts", the theory solver is the engine, and its explanations are
provenance. What makes such a pairing work is always the same thing:
the explanation has to be *general*. "Not this assignment" teaches the
solver one fact; "never r2 with r5" teaches it a quarter of the space.
A Datalog engine is unusually good at this job, because lesson 8's
semirings already compute, for every answer, exactly which inputs it
depended on.

You have seen this pairing once already. Lesson 5's `--models` hands
the same solver one variable per ground *atom*, lets the
Gelfond–Lifschitz check judge each proposal, and turns a refused one
into a clause about its unfounded set. Different theory, different
explanations, the same forty lines in the middle.

Real systems hand the SAT side to an industrial solver, which learns
clauses of its own from every dead end (conflict-driven clause
learning) where this one only backs up.

## Recursion that cannot fool it

FOIL's worst moment in lesson 25 was `sg(X, Y) :- sg(Y, X).`: true of
every example, and it derives nothing. Here is the same target, with
that rule deliberately among the candidates. This time the candidates
come from a file, nine guesses of the kind a person might brainstorm:

```
$ python3 synthesis.py programs/kinship.dl --examples programs/sg.examples --candidates programs/sg.candidates -t
target sg/2: 23 positive examples, 58 negative (closed world)
9 candidate rules from programs/sg.candidates
   r1   sg(X, X) :- parent(X, Y).
   r2   sg(X, X) :- parent(Y, X).
   r3   sg(X, Y) :- sg(Y, X).
   r4   sg(X, Y) :- parent(P, X), parent(P, Y).
   r5   sg(X, Y) :- parent(X, P), parent(Y, P).
   r6   sg(X, Y) :- sg(X, Z), sg(Z, Y).
   r7   sg(X, Y) :- parent(P, X), parent(Q, Y), sg(P, Q).
   r8   sg(X, Y) :- parent(X, P), parent(Y, Q), sg(P, Q).
   r9   sg(X, Y) :- parent(P, X), sg(P, Y).
round 1: try {-}: 0 wrong, 23 missing
   missing sg(ada, ada): require one of {r1, r5, r8}
round 2: try {r1}: 0 wrong, 18 missing
   missing sg(ben, cat): require one of {r4, r7, r9}
round 3: try {r1, r4}: 0 wrong, 8 missing
   missing sg(dov, fay): require one of {r7, r9}
round 4: try {r1, r7}: 0 wrong, 0 missing
4 rounds, 3 constraints, 43 evaluations
learned 2 rules:
   sg(X, X) :- parent(X, Y).
   sg(X, Y) :- parent(P, X), parent(Q, Y), sg(P, Q).
run for real: 23 of 23 positive examples derived, 0 of 58 negative
```

`r3` is never asked for. No why-not clause mentions it, because
switching it on never makes a missing fact appear: it only ever
repeats what is already derived. The rule that fooled a search based
on lookup is simply inert to a search based on evaluation.

The answer is worth reading too. Everybody with a child is in their
own generation (`r1`), and the recursion carries that down the tree,
which is how the childless leaves get their pairs. It is not how a
textbook writes same-generation, and it is right on this tree. Whether
it is right on every tree is a different question, and it is lesson
27's.

## What it costs

**The candidates.** The search is over subsets, but somebody has to
write the set. Enumerating does not scale:

| Body atoms | Extra variables | Candidates for `sg` |
|---|---|---|
| 2 | 1 | 40 |
| 2 | 2 | 56 |
| 3 | 1 | 185 |
| 3 | 2 | 562 |

The same-generation rule needs three atoms and two extra variables, so
it is in the last row and in none of the others. Ask for less and the
loop proves, by exhausting the constraints, that the default 40 do not
contain an answer:

```
$ python3 synthesis.py programs/kinship.dl --examples programs/sg.examples
target sg/2: 23 positive examples, 58 negative (closed world)
40 candidate rules: bodies of up to 2 atoms, 1 extra variable
32 rounds, 84 constraints, 746 evaluations
no subset of the candidates fits the examples: widen the candidates (--max-body, --vars, --candidates), or check the examples
```

That "no" is a proof, which FOIL's "giving up" never was. It is a
proof about these 40 rules and nothing wider. The list would have been
longer still without lesson 16: `candidates` keeps a body only if
`minimise` cannot shrink it, since a body with a redundant atom is the
same query as a smaller one already listed.

**The evaluations.** Five rounds took 219 runs of the engine, nearly
all of them inside `why_not`, growing a failing subset. Every run is a
full bottom-up evaluation, which is why ProSynth hands this step to
an engine built for speed (Soufflé).

**No negation.** The why-not argument is monotonicity, and `not` is
exactly what breaks it: with negation, switching a rule on can remove
an answer. `--candidates` refuses a file with `not` in it instead of
learning from an unsound constraint.

## Where the candidates come from

The loop does not care who wrote the candidates. That is the opening
for a language model, and it is a better division of labour than
asking the model for the answer. Proposing forty plausible rules from
a description of the problem is the kind of thing a model is good at
and a search is bad at. Deciding which subset of forty is consistent
with the evidence is the reverse: the model will sound certain either
way, and the loop will not. So the model fills the file, and the
choice among its guesses is made by evaluation, with a constraint
trail anyone can re-run.

What the loop guarantees is narrow, and worth saying exactly. The
rules it returns reproduce the examples. Nothing says they are the
rules anyone meant.

## The neighbourhood

ProSynth sits in a short line of work on synthesising Datalog. ALPS
(2018) searched the same space of candidate rules by walking the
generality ordering lesson 25 named. Difflog (2019) gave each
candidate a weight between 0 and 1 where this lesson has a switch,
evaluated the program over a semiring much like lesson 9's Viterbi,
and followed the gradient. Popper (Cropper and Morel, 2021) keeps the
propose-and-test loop and learns its constraints from the failed
*program* instead of from provenance: one that derives too much rules
out all its generalisations, one that derives too little rules out
all its specialisations. Scallop (2023) builds provenance semirings
into a language meant to sit beside neural networks. The common
thread is this lesson's: the engine's account of *how* it reached an
answer is worth more to a search than the answer.

## Exercises

1. Round 1 of the `ancestor` trace requires one of ten rules. What do
   those ten have in common, and why is `r32`, which looks like it
   belongs with them, not on the list? (List the candidates with `-t`.)
2. Run the sparse `ancestor` examples with `--max-body 1`. Say exactly
   what the result proves, and what it does not.
3. Delete `r7` from a copy of `programs/sg.candidates` and run again
   with `-t`. What does the loop conclude? One why-not clause in the
   trace has a single rule in it: explain why that is the strongest
   thing the loop can learn.
4. The candidates may not use `not`. Write two rules, one with a
   negated literal, such that switching the second rule *on* removes
   an answer the first derived. Which step of the loop would that
   break?
5. FOIL learned `ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).` from
   the complete examples; this lesson learned
   `ancestor(X, Y) :- ancestor(X, Z), ancestor(Z, Y).` from a dozen.
   Find both among the 40 candidates. Why did the solver's "off first,
   highest number first" habit pick the one it did?

Next: [validating rules](27-validating-rules.md) — a rule that fits
its examples is not yet a rule anyone should trust, whoever or
whatever wrote it.
