# Lesson 8 — answers

Verification script for exercise 3: `exercises/08-exact-prob.py`.

**1. All routes s → t, by hand.**

| route | probability |
|---|---|
| s-a-t | 0.9 × 0.9 = **0.81** ← Viterbi's answer |
| s-a-b-t | 0.9 × 0.8 × 0.95 = 0.684 |
| s-b-t | 0.5 × 0.95 = 0.475 |

`reach(s, b)` similarly: max(0.5, 0.9 × 0.8 = 0.72) = **0.72** — the
indirect route through a is more reliable than the direct link.

**2. Drop `link(s, a)` to 0.6.**

s-a-t becomes 0.6 × 0.9 = **0.54** — still the winner (s-b-t stays
0.475, s-a-b-t falls to 0.456). Verified by re-running; the interesting
part is how *close* it gets: single-fact confidence changes reorder
route rankings, which is why systems that reason over model-produced
confidences need exactly this kind of recomputation.

**3. Exact total probability, by world enumeration.**

`python3 exercises/08-exact-prob.py` enumerates all 2⁵ = 32 worlds:

```
exact P(s reaches t)  = 0.934450
Viterbi (best route)  = 0.810000
```

The exact answer must always be ≥ Viterbi, because "some route works"
includes the event "the best route works" — Viterbi is a lower bound
that ignores the redundancy between routes. The gap (0.12) is the value
of the backup paths, and computing it required leaving semirings for
world-counting, precisely the boundary the lesson drew, and precisely
where Scallop-style systems bring in weighted model counting.
