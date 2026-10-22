"""Making EQs: AutoEQ Local's maths and files (fitting, EQ file formats, the online databases, rig conversions,
History, EQs to compare), brought over almost unchanged. service.py is how the rest of the app uses them: one
function per thing to do, taking and answering plain dicts (they were AutoEQ Local's page's /api/... requests).

Nothing here is imported until the EQ part is used, so the tray stays light. Importing it sets the maths libraries'
thread counts first: the fits use small matrices, extra threads only add overhead, and the worker pool already uses
every core (worker processes inherit the environment).
"""
import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
