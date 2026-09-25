"""dirsnap.py：目录快照（比路径也比内容，认改名，可落盘恢复）。"""
from __future__ import annotations

import json


class SnapshotStore:
    def __init__(self):
        self.snapshots = {}
        self.log = []

    def capture(self, name: str, files: dict) -> dict:
        self.snapshots[name] = {path: tuple(info) for path, info in files.items()}
        self.log.append(("capture", name))
        return {"files": len(self.snapshots[name])}

    def diff(self, old: str, new: str) -> dict:
        """四类差分：新增、删除、内容变化、重命名；传输量只算新增与内容变化。"""
        before = self.snapshots.get(old, {})
        after = self.snapshots.get(new, {})
        added = set(after) - set(before)
        removed = set(before) - set(after)
        modified = sorted(path for path in set(before) & set(after)
                          if before[path][0] != after[path][0])

        removed_by_hash = {}
        for path in sorted(removed):
            removed_by_hash.setdefault(before[path][0], []).append(path)
        added_by_hash = {}
        for path in sorted(added):
            added_by_hash.setdefault(after[path][0], []).append(path)

        renamed = []
        for digest in sorted(removed_by_hash):
            old_candidates = removed_by_hash[digest]
            new_candidates = added_by_hash.get(digest, [])
            if len(old_candidates) == 1 and len(new_candidates) == 1:
                renamed.append([old_candidates[0], min(new_candidates)])
        renamed.sort()

        renamed_old = {pair[0] for pair in renamed}
        renamed_new = {pair[1] for pair in renamed}
        added = sorted(added - renamed_new)
        removed = sorted(removed - renamed_old)

        transfer_bytes = sum(after[path][1] for path in added + modified)
        return {"added": added, "removed": removed, "modified": modified,
                "renamed": renamed, "transfer_bytes": transfer_bytes}

    def apply(self, base: str, changes: dict) -> dict:
        """用旧快照与差分还原新快照，返回 files（路径 → [哈希, 字节数]）。"""
        before = self.snapshots.get(base, {})
        files = {path: list(info) for path, info in before.items()}
        for path in changes.get("removed", []):
            files.pop(path, None)
        for old_path, new_path in changes.get("renamed", []):
            info = files.pop(old_path, None)
            if info is not None:
                files[new_path] = info
        pending = list(changes.get("added", [])) + list(changes.get("modified", []))
        if pending:
            target = self._find_target(set(files) | set(pending), exclude=base)
            for path in pending:
                files[path] = list(target[path])
        return {"files": files}

    def _find_target(self, paths: set, exclude: str = None) -> dict:
        """在已知快照里找路径集合一致的目标版本（取最近的一次）。"""
        for name in reversed(list(self.snapshots)):
            if name == exclude:
                continue
            snapshot = self.snapshots[name]
            if set(snapshot) == paths:
                return snapshot
        raise KeyError("没有与差分匹配的目标快照")

    def persist(self) -> bytes:
        """把快照操作日志落盘成字节流（每行一条 JSON 记录）。"""
        lines = []
        for entry in self.log:
            if entry[0] == "capture":
                name = entry[1]
                record = {"op": "capture", "name": name,
                          "files": {path: list(info) for path, info in self.snapshots[name].items()}}
                lines.append(json.dumps(record, ensure_ascii=False))
        return ("\n".join(lines) + "\n").encode("utf-8") if lines else b""

    def restore(self, blob: bytes = None) -> dict:
        """从字节流恢复快照；尾部半条记录（未换行结尾）忽略。"""
        self.snapshots = {}
        self.log = []
        if not blob:
            return {"snapshots": 0}
        text = blob.decode("utf-8")
        lines = text.split("\n")
        if not text.endswith("\n"):
            lines = lines[:-1]
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("op") == "capture":
                self.capture(record["name"],
                             {path: tuple(info) for path, info in record["files"].items()})
        return {"snapshots": len(self.snapshots)}

    def stats(self) -> dict:
        return {"snapshots": len(self.snapshots), "files": sum(len(items) for items in self.snapshots.values())}
