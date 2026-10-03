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
the same program goes through naive evaluation, magic sets and (for
positive programs) tabling, and each must agree. One external program
thus tests four engines against each other as well as against the
outside world. CI runs it on every push.

## What it does not run, and why

| Cases | Reason |
|---|---|
| 22 from LUBM and hmmer | 10⁵ facts. Joins here are nested loops on purpose ([README](../README.md#what-this-is-not-and-what-is-missing-on-purpose)), so these run for hours, not seconds. |
| 3 using `+` or `-` | Arithmetic is the course's deliberate omission ([lesson 14](../lessons/14-arithmetic.md)). |
| all defeasible theories | A different logic, not Datalog with extra syntax. |

Each skip is a capability the course chose not to have, never a bug.
`run.py` names them in `SKIP`, and anything else that fails, fails the
run.

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
