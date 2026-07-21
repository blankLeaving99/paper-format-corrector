"""Conflict resolver for template synchronization using 3-way merge strategy."""

from __future__ import annotations

from typing import Any


class ConflictResolver:
    """Resolves conflicts between local and remote template versions using 3-way merge."""

    def resolve(self, local: dict, remote: dict, base: dict | None = None) -> dict:
        """Merge two config dicts.

        Strategy:
        - If base is provided: standard 3-way merge (base vs local, base vs remote).
          If both changed from base on the same key and to different values → conflict marker.
        - If base is None: fall back to timestamp-based priority.
          Same key with different values → conflict marker.

        Returns:
            Merged dict. Conflicting fields are wrapped in:
            {"local": <val>, "remote": <val>, "conflict": True}
        """
        if base is not None:
            return self._three_way_merge(local, remote, base)
        return self._two_way_merge(local, remote)

    def _two_way_merge(self, local: dict, remote: dict) -> dict:
        """Simple two-way merge: identical values stay, different values get conflict markers."""
        merged: dict[str, Any] = {}
        all_keys = set(local.keys()) | set(remote.keys())

        for key in all_keys:
            in_local = key in local
            in_remote = key in remote

            if in_local and in_remote:
                local_val = local[key]
                remote_val = remote[key]
                if local_val == remote_val:
                    merged[key] = local_val
                else:
                    merged[key] = {"local": local_val, "remote": remote_val, "conflict": True}
            elif in_local:
                merged[key] = local[key]
            else:
                merged[key] = remote[key]

        return merged

    def _three_way_merge(self, local: dict, remote: dict, base: dict) -> dict:
        """Standard 3-way merge using base as the common ancestor."""
        merged: dict[str, Any] = {}
        all_keys = set(local.keys()) | set(remote.keys()) | set(base.keys())

        for key in all_keys:
            in_base = key in base
            in_local = key in local
            in_remote = key in remote

            base_val = base.get(key)
            local_val = local.get(key)
            remote_val = remote.get(key)

            local_changed = in_local and local_val != base_val
            remote_changed = in_remote and remote_val != base_val

            if not local_changed and not remote_changed:
                # Neither side changed from base — keep base value (or absent)
                if in_base:
                    merged[key] = base_val
                elif in_local:
                    merged[key] = local_val
                else:
                    merged[key] = remote_val
            elif local_changed and not remote_changed:
                # Only local changed — take local
                merged[key] = local_val
            elif remote_changed and not local_changed:
                # Only remote changed — take remote
                merged[key] = remote_val
            elif local_val == remote_val:
                # Both changed to the same value
                merged[key] = local_val
            else:
                # Both changed to different values — conflict
                merged[key] = {"local": local_val, "remote": remote_val, "conflict": True}

        return merged

    @staticmethod
    def has_conflicts(merged: dict) -> bool:
        """Check if a merged result contains any conflict markers."""
        for value in merged.values():
            if isinstance(value, dict) and value.get("conflict") is True:
                return True
        return False

    @staticmethod
    def list_conflicts(merged: dict) -> list[str]:
        """Return a list of keys that have conflict markers."""
        conflicts = []
        for key, value in merged.items():
            if isinstance(value, dict) and value.get("conflict") is True:
                conflicts.append(key)
        return conflicts
