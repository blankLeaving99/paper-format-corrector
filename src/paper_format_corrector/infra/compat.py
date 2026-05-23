"""Runtime dependency compatibility checker.

Verifies that all required and optional packages are installed
with compatible versions. Returns warnings for missing optional deps
and raises errors for missing required deps.
"""

from __future__ import annotations

import sys
from importlib.metadata import version, PackageNotFoundError


# (package_name, pip_name, min_version, max_major, required)
_DEPS = [
    ("docx", "python-docx", "1.1.0", 2, True),
    ("yaml", "pyyaml", "6.0", 7, True),
    ("lxml", "lxml", "5.0", 7, True),
    ("PIL", "Pillow", "9.0", 11, True),
]

_OPTIONAL_DEPS = [
    ("gradio", "gradio", "4.0.0", None, False),
    ("tkinterdnd2", "tkinterdnd2", "0.4.0", None, False),
    ("docx2pdf", "docx2pdf", "0.1.8", None, False),
    ("mammoth", "mammoth", "1.6.0", None, False),
    ("pdfplumber", "pdfplumber", "0.10.0", None, False),
]


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse version string to tuple for comparison."""
    parts = []
    for p in v.split(".")[:3]:
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts) if parts else (0,)


def check_dependencies() -> list[str]:
    """Check all dependencies and return a list of warning messages.

    Returns:
        List of warning strings. Empty list means all OK.
    """
    warnings = []

    # Check required deps
    for import_name, pip_name, min_ver, max_major, required in _DEPS:
        try:
            __import__(import_name)
        except ImportError:
            if required:
                warnings.append(f"[ERROR] Missing required package: {pip_name}>={min_ver}")
            continue

        try:
            installed = version(pip_name)
        except PackageNotFoundError:
            continue

        installed_tuple = _parse_version(installed)
        min_tuple = _parse_version(min_ver)

        if installed_tuple < min_tuple:
            warnings.append(
                f"[ERROR] {pip_name} {installed} is too old, need >={min_ver}"
            )

        if max_major is not None and installed_tuple[0] >= max_major:
            warnings.append(
                f"[WARNING] {pip_name} {installed} may be incompatible (expected <{max_major}.0)"
            )

    # Check optional deps
    for import_name, pip_name, min_ver, _, _ in _OPTIONAL_DEPS:
        try:
            __import__(import_name)
        except ImportError:
            warnings.append(f"[INFO] Optional package not installed: {pip_name}>={min_ver}")

    return warnings


def print_dependency_status() -> None:
    """Print dependency status to console."""
    warnings = check_dependencies()
    if not warnings:
        print("All dependencies OK.")
        return

    for w in warnings:
        if "[ERROR]" in w:
            print(f"  {w}")
        elif "[WARNING]" in w:
            print(f"  {w}")
        else:
            print(f"  {w}")


def require_compatible() -> None:
    """Check dependencies and raise if required ones are missing.

    Called at startup to ensure the environment is usable.
    """
    warnings = check_dependencies()
    errors = [w for w in warnings if "[ERROR]" in w]
    if errors:
        msg = "Dependency issues found:\n" + "\n".join(f"  {e}" for e in errors)
        raise RuntimeError(msg)
