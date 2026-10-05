"""Launcher for the Prolog reader, which lives in
tiny_datalog/prolog.py; an install gets the `tiny-datalog-prolog`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.prolog import main

if __name__ == "__main__":
    sys.exit(main())
