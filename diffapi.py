"""diffapi.py：对外门面（老接口 capture/diff 不能改）。"""
from __future__ import annotations

from dirsnap import SnapshotStore


class Repo:
    def __init__(self):
        self.store = SnapshotStore()

    def capture(self, name: str, files: dict) -> dict:
        return self.store.capture(name, files)

    def diff(self, old: str, new: str) -> dict:
        return self.store.diff(old, new)

    def apply(self, base: str, changes: dict) -> dict:
        return self.store.apply(base, changes)

    def snapshot_bytes(self) -> bytes:
        return self.store.persist()

    def rebuild(self, blob: bytes = None) -> dict:
        return self.store.restore(blob)
