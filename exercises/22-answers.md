# Lesson 22 — answers

Runnable rules: `exercises/22-answers.dl` (exercises 4 and 6; run it
with `chase.py`).

**1. A range for `reportsTo`.**

`triple(reportsTo, range, employee).` makes every object of
`reportsTo` an employee, and so a person: `erin` gains `type employee`
and `type person` (11 `type` triples in all, up from 9), and `dana`,
already both, gains nothing. No new clash appears, because nothing new
is typed as a team. The new axiom is still an inference, not a check:
had someone written `triple(alice, reportsTo, sales)`, the range rule
would make sales an employee too, and that would surface as a clash
only because of the disjointness axiom.

**2. Which fix?**

Change the data (delete or correct `triple(sales, reportsTo, erin)`),
or change the schema (drop the disjointness, or give `reportsTo` a
domain that teams may have). A curator should almost always fix the
data. The schema says teams are not people, which is true, and
weakening it to accommodate one bad triple makes every future bad
triple invisible. But the clash rule cannot decide between the two.
It proves only that the graph and the schema are inconsistent
*together*, and its derivation shows every premise involved. Choosing
which premise to give up is a judgement about which source is more
trustworthy, which is lesson 17's division of labour: the engine
narrows the question, and a person answers it.

**3. Managers working in *some* department.**

With `works_in(M, D2) :- manages(M, D).` the restricted chase no
longer stops (try it with `--max-nulls 50`). The invented manager
`_:n3` of `_:n1` is an employee, so the rule "every employee works in
some department" fires for them. Before, its conclusion was already
satisfied, because `_:n3` worked in `_:n1`, the department they
manage. Now nothing ties `_:n3` to any department until a rule invents
one, and the employee rule runs first and invents `_:n5`, which needs
a manager, who is an employee, and so on. The weak acyclicity report
changes too: the cycle `dept[1] =*=> manages[1] =*=> works_in[2] ->
dept[1]` now has two marked edges, since both of the rules on it
invent values. The lesson's version terminated only because one rule
reused a value instead of inventing one, which no static check could
see.

**4. A weakly acyclic family tree.**

```prolog
person(ada).
parent(P, C)  :- person(C).
ancestor(P)   :- parent(P, _).
```

Invented parents are `ancestor`s, not `person`s, so they never trigger
the parent rule again. The chase invents one null and stops, and
`chase.py` reports the rules weakly acyclic. What it still says
usefully: every recorded person has a parent, and `ancestor(_:n1)` is
a certain answer to "does ada have an ancestor?" (the boolean question)
though not to "who?". What it gave up is the claim that ancestors are
people with parents of their own, which is exactly the claim that
could not be finitely materialised.

**5. A sixth name, and a second supplier.**

With n names for one supplier, `same` among them has n² facts. Adding
`acme_eu` (with one triple of its own) takes the program from five
names to six:

| | five names | six names | plus a two-name second supplier |
|---|---|---|---|
| `same` | 31 | 43 | 49 |
| `copy` | 30 | 42 | 46 |
| `ctriple` | 6 | 7 | 9 |

`same` is 36 for the supplier, plus one reflexive fact for each of the
7 other nodes. `copy` is the supplier's 6 triples on each of 6 names,
plus `order_77`'s one triple with each of 6 objects. `ctriple` grows by
one, the one new statement. The second supplier, `zenith` and
`zenith_ltd`, adds 4 `same` facts, 2 reflexive ones for its new
objects, 4 copies and 2 canonical triples. It is never merged with
acme, because no chain of `sameAs` facts connects them. Equality
classes are the connected components of the `sameAs` graph, which is
exactly what union-find maintains.

**6. Containment under a rule.**

Freeze `q(E) :- employee(E).` into the database `employee(e)` and
chase it with the rule: the chase adds `works_in(e, _:n2)`. Now the
other query's body, `employee(E), works_in(E, D)`, maps into the
chased database with `E = e` and `D = _:n2`, keeping the head. So on
every database that satisfies the rule, the two queries return the
same answers, though lesson 16's plain containment test would say the
second is strictly smaller. This is how the chase decides containment
under constraints (Johnson and Klug, 1984): chase the frozen body
first, then search for the homomorphism as before. The nulls are
exactly lesson 16's frozen variables, invented by a rule instead of by
freezing.
