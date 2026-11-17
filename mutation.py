"""Launcher for the mutation tester for rules, which lives in
tiny_datalog/mutation.py; an install gets the `tiny-datalog-mutation`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.mutation import main

if __name__ == "__main__":
    sys.exit(main())
