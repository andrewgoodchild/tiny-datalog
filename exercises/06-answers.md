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

**4. Writing `h : why → minplus`.**

```python
def h(why_value, weights):
    return min(sum(weights[f] for f in witness) for witness in why_value)
```

Verified against `--semiring minplus` on all ten `path` facts by
`exercises/06-homomorphism.py`. The axiom that takes thought is
**times**: why's `times` is *pairwise union* of witness sets (every
combination of one witness from each side), and it must land on `+`.
It does, because the cost of a union of disjoint fact sets is the sum
of their costs — and where the sets overlap, the shared fact is counted
once on the left and twice on the right. That is the one case worth
checking by hand; it is exactly why min-plus over *sets* behaves and
counting over sets does not.

**5. Breaking `why → count`, and why `why → bool` is safe.**

Any program where one conclusion has two derivations over the same base
facts will do; `programs/06-two-derivations.dl` uses a second rule that
adds an already-implied literal. The sharpest form is the one the
shipped program produces: `p(a, c)` and `q(a, c)` end up with
*identical* why-values but counts of 1 and 2, so no function of the
why-value can be correct for both.

`why → bool` cannot be broken this way because bool has already thrown
away strictly more than why has: it records only *whether* a fact is
derivable, and both a one-derivation and a two-derivation fact are
simply true. Sending every non-empty witness collection to `true` and
the empty one to `false` respects both operations. The general rule is
that you can always specialise *down* a chain of quotients — polynomial
→ why → bool — and never back up it.
