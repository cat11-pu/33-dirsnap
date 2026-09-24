"""dirsnap.py：目录快照（基线：只比路径集合）。"""
from __future__ import annotations


class SnapshotStore:
    def __init__(self):
        self.snapshots = {}
        self.log = []

    def capture(self, name: str, files: dict) -> dict:
        self.snapshots[name] = {path: tuple(info) for path, info in files.items()}
        self.log.append(("capture", name))
        return {"files": len(self.snapshots[name])}

    def diff(self, old: str, new: str) -> dict:
        """基线：只算新增与删除，不看内容也不认改名。"""
        before = self.snapshots.get(old, {})
        after = self.snapshots.get(new, {})
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        return {"added": added, "removed": removed, "modified": [], "renamed": [],
                "transfer_bytes": sum(after[path][1] for path in added)}

    def apply(self, base: str, changes: dict) -> dict:
        raise NotImplementedError("按差分还原还没实现")

    def persist(self) -> bytes:
        raise NotImplementedError("快照还没实现")

    def restore(self, blob: bytes = None) -> dict:
        raise NotImplementedError("重启恢复还没实现")

    def stats(self) -> dict:
        return {"snapshots": len(self.snapshots), "files": sum(len(items) for items in self.snapshots.values())}
