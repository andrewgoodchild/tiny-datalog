# Lesson 5 — Beyond stratification: stable models and the café paradox

Lesson 3 ended on a cliffhanger: the engine rejects any program with
negation inside a recursive cycle, but among the rejected programs some
are perfectly meaningful and some are genuinely paradoxical. Telling them
apart needs real semantics. This engine ships both classical answers
behind the `--models` flag.

## Stable models

A set of facts M is a **stable model** (Gelfond–Lifschitz, 1988) if it
justifies itself: assume M is exactly what's true, simplify every `not`
against that assumption, and check that the simplified (now
negation-free) program derives exactly M back. No dropped conclusions, no
unsupported beliefs.

The win/move game (`programs/03-win.dl`, from Lesson 3) shows why this
is the right notion:

```prolog
move(a, b).  move(b, a).
win(X) :- move(X, Y), not win(Y).
```

```
$ python3 datalog.py --models programs/03-win.dl
Syntactic check: not stratifiable (win --not--> win).
Stable models: 2
  model 1: win(a).
  model 2: win(b).
```

Unstratifiable — yet meaningful: the two stable models are the two
self-consistent ways the game could be. (Answer Set Programming, and the
solver clingo, is this idea industrialized: write programs whose stable
models *are* the solutions to your problem.)

At the other extreme, `p :- not p.` has **no** stable model: assume p
false and the rule derives it; assume p true and nothing supports it. A
program with no stable model is genuinely, semantically paradoxical.

## The well-founded model

The **well-founded semantics** (Van Gelder–Ross–Schlipf, 1991) refuses to
guess. It's three-valued — every fact comes out *true*, *false*, or
*undefined* — and it always exists. For win/move it makes both `win(a)`
and `win(b)` undefined; for `p :- not p.` it makes p undefined. What it
can settle, it settles; what is genuinely circular, it names as such.

## The café paradox

Now the capstone: the café paradox. A town's policy:
anyone who does **not** live in a household that cooks its own meals may
eat free in the café. The café is operated by one of the households, and
Bob — a member of that household — is assigned to cook the café's meals.
Where will Bob take his meals?

Encode "a household cooks its own meals" as being about the meals its
members actually eat (`programs/05-cafe-paradox.dl`), and you get a cycle:
Bob eats in the café iff his household doesn't cook, but his household
cooks — its meals are cooked by its own member, Bob — iff Bob eats in the
café. The engine rejects it syntactically, and `--models` delivers the
semantic verdict:

```
Stable models: none — no consistent two-valued model exists.
Well-founded model (three-valued):
  true:      eats_at_home(alan).  eats_at_home(alice).
             eats_in_cafe(carol).  household_cooks(house_a).
  undefined: eats_at_home(bob).  eats_in_cafe(bob).  household_cooks(cafe_house).
```

This is the barber paradox in catering form — the ground core is
`p :- not p` stretched over two atoms — and the well-founded model is
wonderfully precise about it: everyone else's meals are settled, and
exactly Bob's three facts are undefined. *Where will Bob take his meals?
Undefined.*

Two further encodings complete the story:

- `programs/05-cafe-constraint.dl` — read the argument directly (Bob
  cooks the café's meals, the café is his household, therefore his
  household cooks). The program stratifies, and the paradox reappears as
  a *data-level* integrity violation naming exactly Bob:
  `violation(bob).` Modelling choices decide whether a paradox lives in
  your rules or your data.
- `programs/05-cafe-foodary.dl` — the resolution: the café's food is
  delivered from another town, nobody local cooks it, the cycle is gone,
  and `eats_in_cafe(bob)` holds. Change the situation, not the rule.

## The moral

Three programs, one story, three verdicts:

| Encoding | Syntactic | Semantic |
|---|---|---|
| self-referential | rejected | no stable model; Bob undefined in WFS |
| direct | stratifies | model exists; `violation(bob)` |
| Foodary | stratifies | model exists; Bob eats free |

A sensible-sounding policy can be formally paradoxical, the paradox can
be localized to a single individual, and whether it shows up as "no
model" or "constraint violated" is a modelling choice. A reasoning system
worth trusting detects all of this rather than silently picking an
answer.

## Is this real, or just academic?

The stable-model branch became answer set programming, and ASP earns
money in exactly the places its "models = solutions" shape fits:
industrial product configuration (Siemens has run ASP-based
configurators for years), workforce and transport scheduling, and
bioinformatics pipelines — clingo is the workhorse. The well-founded
semantics runs inside XSB-derived compliance and policy systems. And the
café-paradox skill itself — detecting that a policy is *inconsistent*
rather than silently picking an answer — is precisely what regulated
industries pay for in rule-validation tooling. Niche compared to SQL?
Yes. Academic? The train timetable disagrees.

## Exercises

1. Run `--models` on the barber program (`programs/03-barber.dl`).
   Which fact is undefined? Which is *true* despite the paradox?
2. Give win/move an acyclic move graph (a chain). How many stable models
   now? What does that say about where the ambiguity came from?
3. Invent a third reading of the café: make `household_cooks` an EDB
   fact you assert or don't. What happens in each case?

Next: [semirings](06-semirings.md) — what a derivation carries besides
truth.
