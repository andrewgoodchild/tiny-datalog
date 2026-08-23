# Lesson 6 — answers

Runnable program: `exercises/06-answers.dl` (routes plus a new direct
edge `a → d @ 3`).

**1. Predict all three semirings for `path(a, e)`.**

| semiring | value | reading |
|---|---|---|
| minplus | **6** | the new a→d (3) + d→e (3) beats the old best 7 |
| count | **4** | a-b-d, a-c-d, a-b-c-d, and now a-d — each continued to e |
| why | 4 witness sets | one per route; the new `{edge(a,d), edge(d,e)}` joins the three old sets |

One fact changed; the cheapest route, the route count, and the evidence
sets all moved — same program, three questions.

**2. Weights as multiplicities (bag semantics).**

If `@ n` meant "n parallel copies of the edge", `count` would multiply
along a path and sum across paths: on the original `06-routes.dl`,
path(a, d) = 1×4 (a-b-d) + 2×2 (a-c-d) + 1×1×2 (a-b-c-d) = **10**.
(Amusingly, this repo's count semiring briefly *did* behave this way
during development — the code-review process caught it as a bug, which
it is under set semantics, and a feature, which it is under bag
semantics. Semantics decisions are exactly this consequential.)

**3. A "longest path" semiring.**

(max, +) — max across routes, sum along a route. On any cyclic graph it
diverges for the same reason counting does: going around the cycle once
more always produces a longer path, so no fixpoint exists — the answer
is genuinely infinite. Divergence isn't an implementation weakness;
it's the semiring faithfully reporting that the question has no finite
answer. (Idempotent min never has this problem: extra laps only ever
lose.)
