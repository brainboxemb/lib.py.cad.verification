"""Public import-boundary tests for optional CAD verification stacks."""

from __future__ import annotations

import subprocess
import sys
import unittest


class PublicImportBoundaryTests(unittest.TestCase):
    def run_python(self, source: str) -> None:
        """Run one isolated interpreter against the installed library."""

        completed = subprocess.run(
            [sys.executable, "-I", "-c", source],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=completed.stdout + completed.stderr,
        )

    def test_solidcraft_api_does_not_load_geometry_or_visual_stacks(self):
        self.run_python(
            r'''
import builtins
import sys

real_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if (
        name == "trimesh"
        or name.startswith("trimesh.")
        or name == "PIL"
        or name.startswith("PIL.")
    ):
        raise RuntimeError(f"optional stack imported: {name}")
    return real_import(name, *args, **kwargs)

builtins.__import__ = guarded_import

from cad_verification import (\n    SolidCraftVerification,\n    load_solidcraft_verification,\n    run_solidcraft_verification,\n    run_solidcraft_verification_file,\n)\n\nassert SolidCraftVerification is not None\nassert callable(load_solidcraft_verification)\nassert callable(run_solidcraft_verification)\nassert callable(run_solidcraft_verification_file)\nassert "cad_verification.geometry" not in sys.modules
assert "cad_verification.visual" not in sys.modules
'''
        )

    def test_lazy_geometry_and_visual_exports_remain_public(self):
        self.run_python(
            r'''
from cad_verification import ExpectedBox, GeometryContract

assert ExpectedBox.__module__ == "cad_verification.visual"
assert GeometryContract.__module__ == "cad_verification.geometry"
'''
        )


if __name__ == "__main__":
    unittest.main()
