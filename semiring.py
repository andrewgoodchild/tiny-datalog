"""Launcher for provenance-weighted evaluation, which lives in
tiny_datalog/semiring.py; an install gets the `tiny-datalog-semiring`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.semiring import main

if __name__ == "__main__":
    sys.exit(main())
