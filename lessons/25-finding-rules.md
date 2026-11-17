# Lesson 25 — Finding rules: FOIL, and what greed costs

> Needs lessons 1–3. Lesson 16 (containment) is used once, to name
> something. Lessons 25–27 are one arc: two ways to find rules, then
> how to check rules whoever found them.

Every lesson so far has run in one direction: rules and facts go in,
more facts come out. This one runs it backwards. You have the facts
that should come out, and you want the rules.

That is a real situation, not a party trick. Somebody hands you a
spreadsheet of decisions already made and asks what the policy was. A
knowledge graph has ten million edges and no schema. A language model
proposed a rule and you would like a second opinion that did not come
from a language model. The field that studies it is **inductive logic
programming**, and its first widely used algorithm, Quinlan's FOIL
(1990), fits in one file.

## The problem

Three inputs:

- **Background facts.** What is already known. Here, a family tree with
  nothing derived from it:

  ```prolog
  % programs/kinship.dl        parent(Parent, Child)
  parent(ada, ben).     parent(ada, cat).
  parent(ben, dov).     parent(ben, eve).
  parent(cat, fay).
  parent(dov, gus).
  parent(fay, hal).     parent(fay, ivy).
  ```

- **Positive examples.** Facts the rules must derive.
- **Negative examples.** Facts the rules must not derive.

The output is a set of rules for one **target** predicate that derives
every positive example and no negative one.

Examples are written in the language itself. A fact is a positive
example, and `:- fact.`, which lesson 17 read as "this must never
hold", is a negative one:

```prolog
% programs/grandparent.examples
grandparent(ada, dov).  grandparent(ada, eve).  grandparent(ada, fay).
grandparent(ben, gus).  grandparent(cat, hal).  grandparent(cat, ivy).
```

That file has no negative examples, and it does not need any. Nine
people make 81 pairs, six are listed, and the other 75 are taken to be
negative. This is lesson 4's closed world, used as a source of
training data: whatever was not said is false. It is a strong
assumption, and the second half of this lesson is about what happens
when it is not true.

## FOIL, running

```
$ python3 foil.py programs/kinship.dl --examples programs/grandparent.examples
target grandparent/2: 6 positive examples, 75 negative (closed world)
rule 1: 6 positive examples to cover
   + parent(X, Z)             gain   5.44   10+ 62-
   + parent(Z, Y)             gain  17.09   6+ 0-
   grandparent(X, Y) :- parent(X, Z), parent(Z, Y).   covers 6
learned 1 rule:
   grandparent(X, Y) :- parent(X, Z), parent(Z, Y).
run for real: 6 of 6 positive examples derived, 0 of 75 negative
```

It found lesson 1's rule. Here is how.

FOIL starts with the most general rule there is: the head alone,
`grandparent(X, Y)`, with an empty body. That rule says everybody is
everybody's grandparent, so it covers all 6 positive examples and all
75 negative ones. Then it **specialises**: it adds one literal to the
body, which can only shrink what the rule covers, and repeats until no
negative example is covered.

Which literal? FOIL tries every one it can build and keeps the best.
"Best" needs a number, and the number is the heart of the algorithm.

## The number: information gain

A rule under construction is judged by its **bindings**: the
substitutions that satisfy the body so far. Each binding is labelled
positive or negative by the example its head came from. At the start
there is one binding per example: 6 positive, 75 negative.

Pick a binding at random and ask whether it is positive. With p
positive and n negative, the answer "yes" carries

    -log2(p / (p + n))   bits

of information: a lot when positives are rare, none when every binding
is positive. At the start that is -log2(6 / 81) = 3.75 bits. A good
literal makes the positive bindings less of a surprise.

Add `parent(X, Z)`. Every binding now has to find a child Z for its X,
and may find several. The trace says `10+ 62-`: ten positive bindings,
62 negative. The surprise drops to -log2(10 / 72) = 2.85 bits, a gain
of 0.91 bits per binding. FOIL multiplies that by the number of old
positive bindings that survived, here all 6:

    gain = 6 × (3.75 − 2.85) = 5.44

The multiplication is what keeps FOIL honest. A literal that kept one
positive binding and no negative ones would be perfectly pure, and
nearly useless.

Now the second step. `parent(Z, Y)` leaves `6+ 0-`: every surviving
binding is positive, the surprise is zero, and the gain is
6 × 2.85 = 17.09. No negative binding is left, so the rule is done.

Notice what `parent(X, Z)` was worth on its own: not much. It ruled
out people with no children and nothing else. Its value was the
variable Z it introduced, which the next literal needed. FOIL took it
because 5.44 happened to be the best on offer. Remember that; the
section on greed comes back to it.

## Under the hood: the search space is the engine's

Open `tiny_datalog/foil.py`. Three things in it are already familiar.

**Trying a literal is one join step.** `Foil._extend` calls
`Engine._join_step`, the same function `substitutions` runs for every
body literal of every rule in lesson 2, and that why-not walks in
lesson 17. A positive literal joins: each binding extends once per
matching fact. A negated literal filters. Learning a rule is
evaluating it one literal at a time and counting what is left.

**Safety prunes the search.** `candidates` offers `not p(...)` only
over variables that are already bound, because lesson 3's safety
condition would reject anything else. A learner for a language with no
such rule would have to discover by experiment that those literals are
useless.

**Specialising is containment.** Each literal added makes a rule that
derives a subset of what the rule before it derived, on every
database. That is lesson 16's Q2 ⊇ Q1, and the homomorphism is the
laziest one possible: every atom of the shorter body maps to itself in
the longer one. The learning literature calls the same relation
**θ-subsumption** (Plotkin, 1970), found it seven years before Chandra
and Merlin, and uses it for the same job: ordering rules from general
to specific. FOIL's search is a walk down that ordering, one step at a
time, never back up.

## Recursion, the way FOIL does it

Now the harder target. `programs/ancestor.examples` lists all 17
ancestor pairs in the tree. With `-t`, FOIL shows its five best
candidates at each step before taking one:

```
$ python3 foil.py programs/kinship.dl --examples programs/ancestor.examples -t
target ancestor/2: 17 positive examples, 64 negative (closed world)
rule 1: 17 positive examples to cover
     parent(X, Y)             gain  18.02   8+ 0-
     parent(X, Z)             gain  16.82   30+ 42-
     parent(Z, Y)             gain   2.89   17+ 55-
     not parent(Y, X)         gain   2.55   17+ 56-
   + parent(X, Y)             gain  18.02   8+ 0-
   ancestor(X, Y) :- parent(X, Y).   covers 8
rule 2: 9 positive examples to cover
     parent(X, Z)             gain  10.46   16+ 42-
     parent(Z, Y)             gain   1.71   9+ 55-
     not parent(Y, X)         gain   1.51   9+ 56-
   + parent(X, Z)             gain  10.46   16+ 42-
     ancestor(Z, Y)           gain  16.72   9+ 0-
     parent(Z, U)             gain  13.83   23+ 21-
     parent(Z, Y)             gain  11.15   6+ 0-
     parent(U, Y)             gain   3.43   16+ 34-
     not parent(Y, Z)         gain   3.43   16+ 34-
   + ancestor(Z, Y)           gain  16.72   9+ 0-
   ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).   covers 9
learned 2 rules:
   ancestor(X, Y) :- parent(X, Y).
   ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
run for real: 17 of 17 positive examples derived, 0 of 64 negative
```

Two loops are visible here. The inner one built a rule. The outer one,
the **covering loop**, noticed that the first rule covered only 8 of
the 17 positive examples, set those 8 aside, and asked for another
rule to cover the remaining 9. A rule set is a disjunction, so each
rule only has to cover *some* positives. Every rule has to exclude
*all* negatives.

The second rule is recursive, and one line of the trace deserves a
long look:

```
     ancestor(Z, Y)           gain  16.72   9+ 0-
```

How did FOIL evaluate `ancestor(Z, Y)`? The rules for `ancestor` are
the thing being learned. They do not exist yet. FOIL's answer is to
look the literal up **in the examples**: `ancestor(Z, Y)` is true when
that pair is a positive example. The examples stand in for the
relation they describe.

This is called **extensional** evaluation, and it is the cleverest and
the most dangerous idea in the algorithm. It makes recursion learnable
at the price of one more join. It also means the search never runs
the rules it is building. The line `run for real` at the end is not
part of Quinlan's FOIL. It is there because of what comes next.

## What greed costs

### A rule that is true and derives nothing

Same tree, a different target. Two people are in the same generation
when they are the same number of steps below Ada.
`programs/sg.examples` lists all 23 such pairs, each person with
themselves included.

```
$ python3 foil.py programs/kinship.dl --examples programs/sg.examples
target sg/2: 23 positive examples, 58 negative (closed world)
rule 1: 23 positive examples to cover
   + sg(Y, X)                 gain  41.77   23+ 0-
   sg(X, Y) :- sg(Y, X).   covers 23
learned 1 rule:
   sg(X, Y) :- sg(Y, X).
warning: sg can never hold: every rule for it needs sg first (no base case?)
run for real: 0 of 23 positive examples derived, 0 of 58 negative
```

By FOIL's accounting this is a perfect rule: one literal, all 23
positives covered, no negatives, the highest gain on the board. And it
is *true*. Same-generation is symmetric.

It is also useless. Run it and it derives nothing at all, because a
rule that needs `sg(Y, X)` in order to conclude `sg(X, Y)` has nowhere
to start. The warning is lesson 17's, for exactly this shape, and the
exit status is 3.

The search asked "is this rule true of the examples?" The question
that matters is "does this rule *derive* the examples?" For a rule
with no recursion those are the same question. For a recursive rule
they are not, and extensional evaluation can only ever ask the first.

(Quinlan's FOIL has a guard here. It allows a recursive literal only
when some argument provably gets smaller, under an ordering it
discovers in the data. The guard was there to keep the learned
*Prolog* program from looping forever. Datalog cannot loop forever,
which is lesson 2's theorem, so that motive is gone; the trap is still
there, and a check that runs the rules catches every form of it.)

### Examples that are not complete

Extensional evaluation has a second requirement, and it is the one
that hurts in practice. Looking `ancestor(Z, Y)` up in the examples
only works if the examples contain it. `programs/ancestor.examples`
listed all 17 pairs. Nobody has that. Here are a realistic dozen: six
pairs known to be ancestor and descendant, six known not to be.

```
$ python3 foil.py programs/kinship.dl --examples programs/ancestor-sparse.examples
target ancestor/2: 6 positive examples, 6 negative
rule 1: 6 positive examples to cover
   + parent(X, Y)             gain   3.00   3+ 0-
   ancestor(X, Y) :- parent(X, Y).   covers 3
rule 2: 3 positive examples to cover
   + parent(X, Z)             gain   1.75   5+ 5-
   + parent(Z, U)             gain   3.39   8+ 2-
   + parent(U, V)             gain   1.29   6+ 0-
   + parent(W, Y)             gain   0.00   6+ 0-
   ancestor(X, Y) :- parent(X, Z), parent(Z, U), parent(U, V), parent(W, Y).   covers 2
rule 3: 1 positive example to cover
   + parent(X, Z)             gain   0.22   1+ 5-
   + parent(Z, Y)             gain   2.58   1+ 0-
   ancestor(X, Y) :- parent(X, Z), parent(Z, Y).   covers 1
learned 3 rules:
   ancestor(X, Y) :- parent(X, Y).
   ancestor(X, Y) :- parent(X, Z), parent(Z, U), parent(U, V), parent(W, Y).
   ancestor(X, Y) :- parent(X, Z), parent(Z, Y).
run for real: 6 of 6 positive examples derived, 0 of 6 negative
```

Every example is reproduced, the exit status is 0, and the answer is
wrong. There is no recursion in it. The step FOIL needed is
`ancestor(Z, Y)` after `parent(X, Z)`, and for the example
`ancestor(ada, gus)` that means finding `ancestor(ben, gus)` among the
positives. It is true, and it is not on the list, so the literal looks
worthless. FOIL covers the examples case by case instead: parents,
grandparents, and a second rule that deserves reading aloud. *Anyone
with a great-grandchild is the ancestor of anyone who has a parent.*

On this tree that happens to be true. Ada is the only person with a
great-grandchild, and everybody else descends from her, so the three
rules derive exactly the 17 real pairs, including the eleven FOIL was
never shown. The rule set is not right. It is right *here*. Let one
stranger in (`--assume` evaluates as though a fact had been added):

```
$ python3 datalog.py --assume 'parent(zed, yan).' -q 'ancestor(ada, yan)' programs/ancestor-foil.dl
?- ancestor(ada, yan)
   ancestor(ada, yan).
   (1 answer)
```

Yan has a parent and Ada has a great-grandchild, so Ada is Yan's
ancestor. Nothing in twelve examples about one family could have said
otherwise, and that is a problem this lesson cannot solve. Lesson 27
comes back to these three rules.

One line of the trace is the engine's doing. `parent(W, Y)` was added
with a gain of 0.00: by then no negative example was covered, but `Y`
was still unbound, and an unsafe rule is no rule (lesson 3). So the
search kept going until something bound it, choosing the literal that
kept the most positive examples.

### No way back

The third cost is in the definition. FOIL takes the best literal at
each step and never reconsiders. A literal whose only value is the
variable it introduces, such as `parent(X, Z)` in the grandparent
rule, is taken only if its own gain happens to be positive and the
best on offer. When it is not, the rule that needed it is out of
reach, and nothing in the algorithm can notice.

### No tolerance for a wrong example

One mislabelled example is enough. This FOIL keeps specialising until
no negative example is covered and keeps adding rules until every
positive one is, so a wrong example either warps a rule or stalls the
search (exercise 4). Quinlan's FOIL stops early when a rule would take
more bits to write down than the examples it explains, which is a
minimum-description-length argument and the first appearance of an
idea that every later noise-tolerant learner uses.

## Where this went

FOIL's descendants fixed its faults one at a time. Progol and Aleph
(Muggleton, 1995 onwards) build the most specific rule that explains
one example and search the space above it, so a useless-looking
literal is never out of reach. AMIE (Galárraga and colleagues, 2013)
mines rules from knowledge graphs, where lesson 4's question is the
whole problem: a graph is open-world, so a missing edge is not a
negative example, and AMIE scores a rule only against subjects the
graph knows *something* about. Lesson 22's graphs are where that
matters.

All of them still build rules a literal at a time and judge recursion
by lookup. The next lesson drops both habits.

## Exercises

1. Before running anything: the first candidate for `ancestor` is
   `parent(X, Y)`, which leaves `8+ 0-` starting from 17 positive and
   64 negative bindings. Compute its gain by hand and check it against
   the trace.
2. Write an examples file for `sibling` over `programs/kinship.dl`
   (two different people with a parent in common; six ordered pairs)
   and run FOIL. Explain what it learns. Then say what rule you wanted,
   and why no sequence of literals this FOIL can build would reach it.
3. `not` is offered only over bound variables, and never on the target
   predicate. Name the lesson each restriction comes from, and write
   the program the second one prevents.
4. Add one false positive example, `ancestor(gus, ada).`, to a copy of
   `programs/ancestor.examples` and run FOIL. Which rule is damaged,
   and how can you tell from the trace that noise is the cause?
5. Adding a literal specialises a rule. Use
   `containment.py --contains` to confirm that
   `grandparent(X, Y) :- parent(X, Z), parent(U, Y).` contains the
   learned rule, and say which homomorphism proves it. Why can the
   same tool not compare the two `ancestor` rules FOIL learned with
   the pair a textbook would write?

Next: [finding rules by selection](26-synthesis.md) — every candidate
rule written down first, a SAT solver choosing among them, and lesson
8's provenance explaining each failure.
