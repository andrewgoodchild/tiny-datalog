"""Launcher for the chase — existential rules — which lives in
tiny_datalog/chase.py; an install gets the `tiny-datalog-chase`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.chase import main

if __name__ == "__main__":
    sys.exit(main())
