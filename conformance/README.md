# External conformance

`tests.py` checks this engine against answers its author worked out.
This directory checks it against answers *other engines* produced:
[datalog-conformance](https://pypi.org/project/datalog-conformance/),
a corpus of programs harvested from Soufflé, Nemo and Crepe with the
results those engines give.

```sh
pip install datalog-conformance==0.1.0   # Python 3.11+, not a dependency
python3 conformance/run.py
```

Every core case runs twice over. First datalog-conformance's own
runner compares our semi-naive answers with the source engine's. Then
the same program goes through naive evaluation, magic sets and
tabling, and each must agree. One external program
thus tests four engines against each other as well as against the
outside world.

Every defeasible theory goes through `tiny_datalog/defeasible.py`
([lesson 18](../lessons/18-defeasible.md)) under each policy the case
names. Its conclusions must also satisfy the relations the proof
theory guarantees: +Δ within +∂, −∂ within −Δ, and no literal both
proved and refuted. CI runs it all on every push: 195 cases pass,
89 core and 106 defeasible.

## What it does not run, and why

| Cases | Reason |
|---|---|
| 44 from LUBM and hmmer, core and lifted | 10⁵ facts. Joins here are nested loops on purpose ([README](../README.md#what-this-is-not-and-what-is-missing-on-purpose)), so these run for hours, not seconds. |
| 4 using `+` or `-` | Arithmetic is the course's deliberate omission ([lesson 14](../lessons/14-arithmetic.md)). |
| 34 strict theories lifted from programs with `not` | Defeasible logic has strong negation (`~`) only, no negation as failure. |
| 7 with declared conflicts | SPINdle lets unrelated literals conflict. In defeasible logic only `p` and `~p` do. |
| 6 checked against DePYsible | DePYsible implements DeLP, which ranks arguments by *specificity*. Defeasible logic infers no priority; you state each one. |
| 2 from Antoniou's ambiguity example | The corpus labels an ambiguous literal `undecided`. The 2001 proof theory proves it −∂, checked clause by clause. |
| 3 on rational and lexicographic closure | A different family of nonmonotonic logics. |

Each skip is a capability the course chose not to have, or a case
written for a different logic, never a bug. `run.py` names each one
with its reason, and anything else that fails, fails the run.

## Translation

The corpus spells Datalog the Soufflé way: any bare name inside an
argument list is a variable, and predicates may be capitalised.
`adapter.py` translates token by token. It also does one rewrite that
goes beyond spelling. Nemo reads a variable that appears only under
`not` as "there is none", and this engine refuses that rule (lessons 3
and 17). For cases harvested from Nemo or Soufflé, the adapter applies
the fix lesson 17 teaches, projecting first. The corpus's own case that
expects the rule to be *refused* is left to the engine's native safety
check, which refuses it.
