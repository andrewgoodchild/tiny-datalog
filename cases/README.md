# Golden test cases

Add a test without writing Python: make a directory here with three
files, and the test suite picks it up automatically.

```
cases/<your-case>/
  program.dl     any Datalog program
  queries        one query atom per line (% comments allowed)
  expected       the answers, exactly as datalog.py prints them:
                 for each query in order, its matching facts sorted
```

Run `python3 tests.py` — a `GoldenFileTests` subtest runs per case. To
(re)generate an `expected` file, run each query with
`python3 datalog.py -q '<query>' program.dl` and copy the answer lines.
