# Lesson 16 — Containment: the same search, one level up

> **Self-contained.** Needs lessons 1–3 only, despite the number.

Every lesson so far asked what a program computes *on this database*.
An optimiser asks a harder question: what does it compute on **every**
database? Two queries that agree on your data may disagree on data you
haven't seen; two that agree everywhere are interchangeable, and the
cheaper one is free performance.

Chandra and Merlin answered this in 1977, and the answer is one you
already have the machinery for.

## The question

Query **containment**: does Q1 return a subset of Q2's answers on every
possible database? Write it Q2 ⊇ Q1. **Equivalence** is containment
both ways. **Minimisation** is finding the smallest body equivalent to
the one you wrote.

Quantifying over all databases sounds undecidable. For conjunctive
queries: a single rule, no negation, no recursion; it isn't:

> **Q2 ⊇ Q1 iff there is a homomorphism from Q2's body into Q1's body
> that fixes the head variables.**

A homomorphism is a map from Q2's variables to Q1's terms sending every
atom of Q2 onto an atom of Q1. Infinitely many databases collapse into
one finite search, because Q1's own body, with its variables frozen
into distinct constants — is the hardest database Q1 can be run on. If
Q2 can be satisfied there, it can be satisfied wherever Q1 is.

## The model theory underneath

Name the frame, because Lesson 18 will claim this lesson runs on it.
**Model theory** studies the relationship between sentences and the
structures that satisfy them; its workhorse map is the
**homomorphism**, a function between structures that preserves every
atomic fact. Two of its standard moves power this whole lesson:

- **The canonical instance.** Freeze Q1's body — treat its variables
  as fresh constants — and you get a database: the smallest, most
  hostile model of Q1. It satisfies Q1 and nothing it isn't forced to.
- **Preservation.** Conjunctive queries are *positive existential*
  formulas, and those are exactly the formulas homomorphisms preserve:
  if Q holds in A and A maps homomorphically into B, Q holds in B. (Add
  negation and preservation fails — which is why this theory refuses
  it.)

Chandra–Merlin is those two moves composed: Q2 holds on *every*
database Q1 matches iff Q2 holds on the canonical one, and "holds on
the canonical one" is exactly "Q2's body maps homomorphically into
Q1's." A statement about all models collapses to one finite check
against the worst model — the same all-worlds-to-one-witness shape as
Lesson 5's grounding envelope.

## Under the hood: you already wrote the search

Open `datalog.py` and read `_match` again:

```python
def _match(args, tup, subst):
    """Extend subst so that args == tup, or return None. ...
    This is one-way unification (pattern matching): `tup` is always
    ground ..."""
```

That maps a rule body into a **database** — atoms whose arguments are
ground. `containment.py`'s `find_homomorphism` maps a rule body into
**another rule body** — atoms whose arguments are variables. Same
backtracking search, same one-way matching, one level up the
abstraction: the target's variables behave exactly like constants.

That is why `containment.py` is short. The interesting part was
already in the engine; the lesson is recognising where else it applies.

## Minimisation, running

`programs/minimise.dl` collects the classic shapes:

```sh
$ python3 containment.py programs/minimise.dl
has_edge(X, Y) :- edge(X, Y), edge(X, Z).
  minimises to has_edge(X, Y) :- edge(X, Y).   (2 atoms -> 1)
two_hop(X) :- edge(X, Y), edge(Y, Z), edge(X, W).
  minimises to two_hop(X) :- edge(X, Y), edge(Y, Z).   (3 atoms -> 2)
mutual(X) :- edge(X, Y), edge(Y, X).
  already minimal (2 atoms)
triangle(X) :- edge(X, Y), edge(Y, Z), edge(Z, X).
  already minimal (3 atoms)
```

Read the first one carefully, because it is the whole idea. `edge(X, Z)`
says "X has *an* outgoing edge", and `edge(X, Y)` already guarantees
that, since Z is free to be Y. The atom's job is done; drop it and the
answers on every database are unchanged. That is a self-join eliminated
by proof, not by pattern-matching on the syntax.

The 2-cycle looks similar and is *not* redundant: folding `edge(Y, X)`
onto `edge(X, Y)` would require sending X to Y, and X is a head
variable — pinned. One head variable is the difference between a free
optimisation and a wrong answer.

Containment on its own:

```sh
$ python3 containment.py --contains 'q(X) :- edge(X, Y).' \
                         'q(X) :- edge(X, Y), edge(Y, Z).'
=> outer contains inner, on every database
```

"Nodes with an outgoing edge" contains "nodes that start a two-hop
path", necessarily and forever.

## What it costs

Homomorphism-finding is NP-complete; it is graph colouring wearing a
different hat, and containment inherits that. The backtracking search
in `containment.py` is the standard practical answer: queries written by
humans are small, and the exponential lives in the number of atoms, not
the size of the data. Optimisers apply minimisation once per query and
then evaluate the minimised form over millions of rows, so an expensive
analysis buys cheap execution: the same trade magic sets makes in
Lesson 7.

## Where the theory stops

Two boundaries, both sharp:

- **Negation.** The homomorphism theorem is a conjunctive-query result.
  Add `not` and containment becomes a different (and harder) problem;
  `containment.py` refuses such rules rather than answering wrongly.
- **Recursion.** Containment of *recursive* Datalog programs is
  undecidable (Shmueli). This is the same wall Lesson 11 hit from the
  other side: the question is decidable exactly where the language is
  restricted enough, and Datalog's recursion is expressive enough to
  break it. Uniform containment: a stronger, sufficient condition — is
  decidable, which is what real systems check.

Notice the pattern the course keeps returning to: a question about all
possible worlds becomes a finite computation only when the language is
deliberately weakened. Function symbols (Lesson 11), negation-in-cycles
(Lesson 3), aggregation-in-cycles (Lesson 13), and now recursion in
containment — four different fences, same reason for the fence.

## The nearest answerable query: views

Containment has a second job, and it is the one that made it
industrial. Suppose you cannot evaluate `q` directly — the base
relation lives in systems you can only reach through a fixed set of
**views**, materialised queries someone else chose. You must rewrite
`q` using only the views, and an *equivalent* rewriting usually does
not exist. The realistic target is the **maximally contained
rewriting**: the largest view-only query that is still ⊑ q on every
database — the nearest query your sources can answer, with soundness
certified by exactly this lesson's test. (The classical treatment is
Halevy's *Answering Queries Using Views* survey; the setting is how
data-integration mediators have worked since the 1990s.)

Three things make the problem interesting, and the exercise below
walks through all of them: a candidate rewriting is checked by
*expanding* its view atoms into base atoms and testing containment;
candidate rewritings can subsume one another (their expansions are
themselves just conjunctive queries); and maximal is not complete — on
some databases the views simply never saw the rows your query needs,
and no rewriting can conjure them back.

## Exercises

1. Minimise by hand, then check: `q(X) :- e(X, Y), e(Y, Z), e(X, U), e(U, V).`
   How many atoms survive, and why is it not one? (Note which pair the
   tool keeps, and convince yourself the other pair would have done
   equally well.)
2. `q(X) :- edge(X, Y), edge(Y, X).` is contained in
   `q(X) :- edge(X, Y).` but not the reverse. Give the one-edge
   database that proves the missing direction, then say which
   homomorphism fails to exist and why.
3. Why must the homomorphism fix head variables? Construct the wrong
   answer you would get without that condition. (Hint: the 2-cycle
   above is the shortest counterexample.)
4. Run `containment.py` over every shipped program. They are all
   already minimal — hand-written teaching queries usually are. So
   where does redundancy actually come from in practice? (Think about
   what happens when a view is inlined into another view, and why
   optimisers minimise *after* rewriting rather than before.)

5. You may query only two views over a private `follows` relation:
   `v_mut(X, Y) :- follows(X, Y), follows(Y, X).` and
   `v_fof(X, Z) :- follows(X, Y), follows(Y, Z), follows(Z, W).`
   The query you want is `q(X, Z) :- follows(X, Y), follows(Y, Z).`
   (a) Expand the candidate rewritings `r1(X, Z) :- v_mut(X, Y),
   v_mut(Y, Z).` and `r2(X, Z) :- v_fof(X, Z).` into base atoms and
   certify each sound with `--contains`. (b) Show, again with
   `--contains` on the expansions, that r1 is subsumed by r2 — so the
   maximally contained rewriting collapses to r2 alone. (c) Exhibit a
   two-fact database where q has an answer that no view-only rewriting
   can recover, and say in one sentence why "maximal" and "complete"
   part company.

Next: [writing rules that survive review](17-writing-rules.md) —
sixteen lessons on how engines evaluate rules, and one on authoring
them.
