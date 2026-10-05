"""Launcher for KL-ONE style classification, which lives in
tiny_datalog/subsumption.py; an install gets the
`tiny-datalog-subsumption` command instead.  Why it is three lines of
delegation that re-export only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.subsumption import main

if __name__ == "__main__":
    sys.exit(main())
