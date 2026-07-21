#!/usr/bin/env python3
"""Architecture verification script.

Checks that dependency flow follows Clean Architecture rules:
  interfaces → application → domain ← infrastructure

Forbidden directions:
  domain → infrastructure ❌
  domain → interfaces ❌
  application → interfaces ❌
  shared → anything ❌

Usage: python scripts/verify_architecture.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SRC = PROJECT_ROOT / "src" / "paper_format_corrector"

# Allowed dependency directions per layer
ALLOWED_DEPS = {
    "interfaces": {"application", "domain", "infrastructure", "shared", "plugins"},
    "application": {"domain", "shared"},
    "domain": {"shared"},
    "infrastructure": {"domain", "shared"},
    "plugins": {"domain", "shared"},
    "shared": set(),  # shared depends on nothing internal
}


def detect_layer(filepath: Path) -> str | None:
    """Detect which architectural layer a file belongs to."""
    try:
        rel = str(filepath.relative_to(SRC))
    except ValueError:
        return None
    for layer in ALLOWED_DEPS:
        if rel.startswith(layer + "/") or rel.startswith(layer + "\\"):
            return layer
    return None


def check_file_imports(filepath: Path, layer: str) -> list[str]:
    """Check if a file violates architecture rules."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []

    errors = []
    allowed = ALLOWED_DEPS.get(layer, set())

    for node in ast.walk(tree):
        targets = []

        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # Handle relative imports
            if node.level and node.level > 0:
                # Relative import — resolve based on file depth
                parts = filepath.relative_to(SRC).parts
                if node.level <= len(parts) - 1:
                    base = parts[node.level - 1] if node.level <= len(parts) else ""
                    if base in ALLOWED_DEPS and base != layer:
                        errors.append(
                            f"  [VIOLATION] {layer} -> {base} (relative import, line {node.lineno})"
                        )
                continue

            if node.module:
                targets.append(node.module)

        for target in targets:
            if target.startswith("paper_format_corrector."):
                parts = target.split(".")
                if len(parts) >= 2:
                    target_layer = parts[1]
                    if target_layer in ALLOWED_DEPS and target_layer != layer:
                        if target_layer not in allowed:
                            errors.append(
                                f"  [VIOLATION] {layer} -> {target_layer} "
                                f"(import: {target}, line {node.lineno})"
                            )

    return errors


def main() -> int:
    """Run architecture verification."""
    import os

    print("[ARCH] Architecture verification...")
    print(f"   Source: {SRC}")
    print()

    all_errors: list[str] = []
    files_checked = 0

    for root, dirs, files in sorted(os.walk(SRC)):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            filepath = Path(root) / fname
            layer = detect_layer(filepath)
            if not layer:
                continue

            files_checked += 1
            errors = check_file_imports(filepath, layer)
            if errors:
                rel = filepath.relative_to(SRC)
                print(f"\n  {rel}")
                for err in errors:
                    print(f"  {err}")
                all_errors.extend(errors)

    print(f"\n{'='*60}")
    print(f"Files checked: {files_checked}")

    if all_errors:
        print(f"[FAIL] Found {len(all_errors)} architecture violations")
        print()
        print("Allowed dependency flow:")
        print("  interfaces -> application -> domain <- infrastructure")
        print("  shared <- (everything, shared has no internal deps)")
        return 1
    else:
        print("[PASS] Architecture verification passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
