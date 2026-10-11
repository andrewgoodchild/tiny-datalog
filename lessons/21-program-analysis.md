# Lesson 21 — Program analysis: when the database is a program

Lesson 0 credited program analysis with bringing Datalog back from its
winter, and lesson 2 showed four rules of a pointer analysis in
passing. This lesson takes the application seriously, because it is
where Datalog runs at the largest scale today: GitHub's **CodeQL**
scans code with an object-oriented Datalog, and the **Doop** framework
expresses a whole family of Java pointer analyses, from the crude to
the very precise, as Datalog rules run by Soufflé.

The idea fits in one sentence. **Turn the program into a database of
facts, write the analysis as rules over it, and read each finding's
derivation as the path through the code that causes it.** Each of the
three steps is a section below. Lessons 1–3 are the prerequisites, and
lesson 7 matters at the end.

Why this application, of all of them? A static analyser must
terminate on every program anyone can write, including the adversarial
ones, and it must be easy to change, because analyses are research and
get rewritten constantly. Datalog guarantees the first by construction
(lesson 2) and makes the second a matter of editing rules rather than
re-engineering a worklist algorithm.

## Step one: the program becomes facts

An analyser never sees source text. A front end (the **extractor**)
walks the parsed program once and emits a relation for each kind of
statement. CodeQL builds a relational database per codebase this way,
and Doop generates its facts from Java bytecode. The analysed program
for this lesson is small enough to extract by hand:

```
class Dog   { Object speak() { return new Bone(); } }     // h3
class Cat   { Object speak() { return new Yarn(); } }     // h4
class Robot { Object speak() { return new Gear(); } }     // h5

main() {
  a = new Dog();        // h1
  b = new Cat();        // h2
  c = a;
  x = c.speak();        // call site s1: which speak?
  y = b.speak();        // call site s2
}
```

and the facts `programs/callgraph.dl` holds for it:

```prolog
alloc(a, h1).        heap_type(h1, dog).
alloc(b, h2).        heap_type(h2, cat).
assign(c, a).
vcall(s1, c, speak, x).            % site, receiver, method name, result
vcall(s2, b, speak, y).
method(dog, speak, dog_speak).     returns(dog_speak, r_dog).
method(cat, speak, cat_speak).     returns(cat_speak, r_cat).
method(robot, speak, robot_speak). returns(robot_speak, r_robot).
```

`h1` is a **heap object**: an abstraction of "whatever the allocation
at this line creates", however many times it runs. An analysis has to
abstract like this somewhere, because the running program can create
unboundedly many objects and the analysis must stay finite. Naming
objects by their allocation site is the classic choice.

## Step two: points-to and the call graph, as one fixpoint

At call site `s1`, which `speak` runs? It depends on what `c` points
to at run time. And what `c` points to depends on which methods ran,
because a call's result points to whatever the callee returned. The
**call graph** needs **points-to** information, and points-to needs the
call graph.

An analyser written by hand has to break that circle somehow: build a
crude call graph first, or code a worklist algorithm that grows both
together and is famously easy to get subtly wrong. In Datalog the
circle is simply mutual recursion, which lesson 2 already handles:

```prolog
pt(V, H) :- alloc(V, H).
pt(V, H) :- assign(V, W), pt(W, H).

% virtual dispatch: resolve a call by what the receiver may point to...
calls(S, M) :- vcall(S, Recv, Name, _), pt(Recv, H),
               heap_type(H, T), method(T, Name, M).
% ...and the call's result points to what the callee returns
pt(V, H) :- vcall(S, _, _, V), calls(S, M), returns(M, R), pt(R, H).
```

```
$ python3 datalog.py -q 'calls(S, M)' -q 'pt(x, H)' programs/callgraph.dl
?- calls(S, M)
   calls(s1, dog_speak).
   calls(s2, cat_speak).
   (2 answers)
?- pt(x, H)
   pt(x, h3).
   (1 answer)
```

That observation, that a precise analysis is short as long as the
language can say "these relations are defined together", is the
thesis of the Doop paper (Bravenboer and Smaragdakis, 2009), whose
title called it *strictly declarative specification*. The engine finds
the joint fixpoint, and termination is not something you had to
argue.

Compare the cheap alternative. **Class hierarchy analysis** (CHA)
resolves a call by its method name alone, with no points-to at all:

```prolog
calls_cha(S, M) :- vcall(S, _, Name, _), method(_, Name, M).
```

```
$ python3 datalog.py -q 'calls_cha(S, M)' programs/callgraph.dl
?- calls_cha(S, M)
   calls_cha(s1, cat_speak).
   calls_cha(s1, dog_speak).
   calls_cha(s1, robot_speak).
   calls_cha(s2, cat_speak).
   calls_cha(s2, dog_speak).
   calls_cha(s2, robot_speak).
   (6 answers)
```

Six edges against two. Every extra edge is a method the analyser must
now assume might run, and everything downstream (taint, nullness,
dead code) inherits the noise. `Robot.speak` is the starkest case.
No `Robot` is ever allocated, so the precise call graph proves it dead
code, and CHA cannot.

As before, the derivation is the reason. Why does `s1` call the dog's
method, and why not the cat's?

```
$ python3 datalog.py --explain 'calls(s1, dog_speak)' --explain 'calls(s1, cat_speak)' programs/callgraph.dl
?- explain calls(s1, dog_speak)
   calls(s1, dog_speak)   [via calls(S, M) :- vcall(S, Recv, Name, _), pt(Recv, H), heap_type(H, T), method(T, Name, M).]
     vcall(s1, c, speak, x)   (base fact)
     pt(c, h1)   [via pt(V, H) :- assign(V, W), pt(W, H).]
       assign(c, a)   (base fact)
       pt(a, h1)   [via pt(V, H) :- alloc(V, H).]
         alloc(a, h1)   (base fact)
     heap_type(h1, dog)   (base fact)
     method(dog, speak, dog_speak)   (base fact)
?- explain calls(s1, cat_speak)
   calls(s1, cat_speak) is not derived.  Per rule:
     via calls(S, M) :- vcall(S, Recv, Name, _), pt(Recv, H), heap_type(H, T), method(T, Name, M).
       blocked at: method(dog, speak, cat_speak) -- no matching fact
```

The negative answer is worth reading twice: the receiver was a dog,
and dogs do not have the cat's method. That is the exact reasoning a
person would give.

## Step three: can untrusted input reach a dangerous call?

The analysis security teams run most is **taint tracking**. Values
from a **source** (request parameters, files) are tainted. Taint
flows through assignments, parameters and returns. A **sink** (a
database query, a shell command) receiving a tainted value is a
finding, unless the value went through a **sanitizer** first.
`programs/taint.dl` analyses this:

```
String id(String p) { return p; }          // a harmless helper

void handle(Request req) {
  q    = req.param("q");                   // SOURCE
  safe = escape(q);                        // sanitizer
  t    = id(q);                            // call site c1
  k    = id("SELECT 1");                   // call site c2
  db.query(t);                             // sink1
  db.query(k);                             // sink2
  db.query(safe);                          // sink3
}
```

The rules are lesson 2's reachability with a different edge relation:

```prolog
flow(F, A) :- call(S, M), actual(S, A), formal(M, F).     % into a parameter
flow(R, X) :- call(S, M), returns(M, X), result(S, R).    % out of a return

tainted(V) :- source(V).
tainted(V) :- flow(V, W), tainted(W).

finding(S, V) :- sink(S, V), tainted(V).
```

The sanitizer has no rule at all. `escape` has no `formal` or
`returns` facts, so no flow passes through it. That is the usual
modelling choice: the analysis does not know what `escape` does, only
that its output is clean.

```
$ python3 datalog.py -q 'finding(S, V)' programs/taint.dl
?- finding(S, V)
   finding(sink1, t).
   finding(sink2, k).
   (2 answers)
```

`sink1` is real. A finding needs a path a developer can follow, and
CodeQL's *path queries* print exactly that. Here the path is the
derivation:

```
$ python3 datalog.py --explain 'finding(sink1, t)' programs/taint.dl
?- explain finding(sink1, t)
   finding(sink1, t)   [via finding(S, V) :- sink(S, V), tainted(V).]
     sink(sink1, t)   (base fact)
     tainted(t)   [via tainted(V) :- flow(V, W), tainted(W).]
       flow(t, p)   [via flow(R, X) :- call(S, M), returns(M, X), result(S, R).]
         call(c1, id)   (base fact)
         returns(id, p)   (base fact)
         result(c1, t)   (base fact)
       tainted(p)   [via tainted(V) :- flow(V, W), tainted(W).]
         flow(p, q)   [via flow(F, A) :- call(S, M), actual(S, A), formal(M, F).]
           call(c1, id)   (base fact)
           actual(c1, q)   (base fact)
           formal(id, p)   (base fact)
         tainted(q)   [via tainted(V) :- source(V).]
           source(q)   (base fact)
```

Bottom to top: `q` is user input, it enters `id` as `p` at `c1`, comes
back out as `t` at `c1`, and reaches the query. `sink3` is correctly
clean, and the engine says why in one line:

```
$ python3 datalog.py --explain 'finding(sink3, safe)' programs/taint.dl
?- explain finding(sink3, safe)
   finding(sink3, safe) is not derived.  Per rule:
     via finding(S, V) :- sink(S, V), tainted(V).
       blocked at: tainted(safe) -- no matching fact
```

## The false positive, and what precision costs

`sink2` is wrong. `k` holds the constant `"SELECT 1"`, and no user
input ever reaches it. Ask the engine why it thinks otherwise:

```
$ python3 datalog.py --explain 'finding(sink2, k)' programs/taint.dl
?- explain finding(sink2, k)
   finding(sink2, k)   [via finding(S, V) :- sink(S, V), tainted(V).]
     sink(sink2, k)   (base fact)
     tainted(k)   [via tainted(V) :- flow(V, W), tainted(W).]
       flow(k, p)   [via flow(R, X) :- call(S, M), returns(M, X), result(S, R).]
         call(c2, id)   (base fact)
         returns(id, p)   (base fact)
         result(c2, k)   (base fact)
       tainted(p)   [via tainted(V) :- flow(V, W), tainted(W).]
         flow(p, q)   [via flow(F, A) :- call(S, M), actual(S, A), formal(M, F).]
           call(c1, id)   (base fact)
           actual(c1, q)   (base fact)
           formal(id, p)   (base fact)
         tainted(q)   [via tainted(V) :- source(V).]
           source(q)   (base fact)
```

The bug is visible in the call sites. Taint went **in at `c1`** and
came **out at `c2`**. The analysis has one `p` for all calls to `id`,
so everything passed to `id` anywhere is mixed together and comes back
everywhere. It is **context-insensitive**: it ignores which call is
running.

This is not a bug in the rules so much as the price of their
simplicity, and it is the central trade of the whole field. An
analysis is **sound** (in the may-analysis sense) if it reports every
real flow. Merging contexts keeps it sound and costs **precision**:
reports that cannot happen. The fixes all add context to the
relations, so that `p` called from `c1` and `p` called from `c2` are
different facts:

- **call-site sensitivity** (k-CFA): tag each callee variable with the
  last k call sites. Exercise 2 does k = 1, and the false positive
  disappears.
- **object sensitivity**: tag with the receiver object instead. This
  works better for object-oriented code, and Doop's best-known results
  are about choosing the context well (Smaragdakis, Bravenboer and
  Lhoták, *Pick Your Contexts Well*, 2011).

Context multiplies facts: every callee variable now exists once per
context, and real programs have deep call chains. That multiplication
is what drove the engineering. bddbddb (Whaley and Lam, 2004) stored
the relations as binary decision diagrams so that cloned contexts
could share structure, and Soufflé compiles Datalog to parallel C++
so that Doop's analyses finish at all. The rules stayed short. The
engines got serious.

## What else is this shape

Most classic analyses are reachability over some relation the
extractor emits, with one of this course's features on top:

| Analysis | Datalog shape | Lesson |
|---|---|---|
| pointer analysis, call graph | mutual recursion | 2 |
| taint, information flow | reachability over flow edges | 2 |
| reaching definitions | reachability with kills: `not` on a base relation | 3 |
| constant propagation, intervals | values from a lattice, not a set | 13 |
| on-demand analysis ("does *this* sink leak?") | magic sets, or tabling | 7, 15 |
| explaining a finding | the derivation | 1, 17 |

The lattice row is where Datalog engines have grown most recently.
Flix and Ascent let a relation carry a lattice value (a constant, an
interval, a sign) and join values instead of adding tuples, which is
lesson 13's closing section put to work.

## Exercises

1. Add `d = new Robot(); z = d.speak();` to `programs/callgraph.dl`
   (allocate `h6`, add a call site `s3`). Predict `calls(S, M)` and
   whether `pt(z, H)` sees `h5` before you run it.
2. Make the taint analysis **1-call-site sensitive**, so a callee's
   parameter is tracked per call site, and show that `sink2` goes away
   while `sink1` stays.
3. **Reaching definitions.** Given `def(D, Var, Node)`, `succ(N1, N2)`
   and the fact that a definition is killed by any later definition
   of the same variable, write `reaches(D, N)`. Which lesson's
   discipline makes the `not` legal?
4. Run `--magic --trace -q 'finding(sink1, V)'` against
   `programs/taint.dl`. Does demand save facts here, or cost them?
   Explain the count with lesson 7's rule, then imagine a
   million-line program with one sink you care about, and say what
   changes.
5. The analysis is a may-analysis: it unions every possibility. Name
   a question that needs a **must**-analysis instead ("on every path,
   …"), and say which of this course's tools turns "every" into
   something Datalog can derive. (Lesson 6.)

Next: [knowledge graphs](22-knowledge-graphs.md), where the facts
describe a world rather than a program, and some of them have to be
invented.
