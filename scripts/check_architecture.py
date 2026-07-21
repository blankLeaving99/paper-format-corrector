#!/usr/bin/env python3
"""CI architecture check - wrapper for verify_architecture.py.

Usage: python scripts/check_architecture.py
Exit code 0 = pass, 1 = violations found.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "verify_architecture.py")],
        cwd=str(project_root),
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
