"""Launcher for the FOIL rule learner, which lives in
tiny_datalog/foil.py; an install gets the `tiny-datalog-foil`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.foil import main

if __name__ == "__main__":
    sys.exit(main())
