"""Launcher for the rule synthesiser, which lives in
tiny_datalog/synthesis.py; an install gets the `tiny-datalog-synthesis`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.synthesis import main

if __name__ == "__main__":
    sys.exit(main())
