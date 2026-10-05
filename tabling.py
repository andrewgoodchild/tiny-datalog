"""Launcher for top-down evaluation with memoing, which lives in
tiny_datalog/tabling.py; an install gets the `tiny-datalog-tabling`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.tabling import main

if __name__ == "__main__":
    sys.exit(main())
