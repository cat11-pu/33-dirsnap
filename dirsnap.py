"""dirsnap.py：目录快照（内容级差分、增量传输、落盘恢复）。"""
from __future__ import annotations

import hashlib
import json
import os


def _canonical(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class SnapshotStore:
    def __init__(self, log_path: str = "dirsnap.log"):
        self.snapshots = {}
        self.log = []
        self.log_path = log_path

    def capture(self, name: str, files: dict) -> dict:
        self.snapshots[name] = {path: tuple(info) for path, info in files.items()}
        self.log.append(("capture", name))
        return {"files": len(self.snapshots[name])}

    def diff(self, old: str, new: str) -> dict:
        """内容级差分：新增、删除、内容变化、改名配对，附增量传输字节数。"""
        before = self.snapshots.get(old, {})
        after = self.snapshots.get(new, {})
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        modified = sorted(
            path for path in set(before) & set(after)
            if before[path][0] != after[path][0]
        )
        renamed, added, removed = self._pair_renames(before, after, added, removed)
        entries = {path: list(after[path]) for path in added + modified}
        transfer = sum(after[path][1] for path in added + modified)
        return {"added": added, "removed": removed, "modified": modified,
                "renamed": renamed, "transfer_bytes": transfer, "entries": entries}

    @staticmethod
    def _pair_renames(before: dict, after: dict, added: list, removed: list):
        """删除侧与新增侧哈希各自唯一时配对，候选取路径字典序最小。"""
        added_by_hash = {}
        for path in added:
            added_by_hash.setdefault(after[path][0], []).append(path)
        removed_by_hash = {}
        for path in removed:
            removed_by_hash.setdefault(before[path][0], []).append(path)
        renamed = []
        used_added = set()
        used_removed = set()
        for old_path in removed:
            digest = before[old_path][0]
            candidates = added_by_hash.get(digest, [])
            if len(removed_by_hash[digest]) == 1 and len(candidates) == 1:
                new_path = min(candidates)
                renamed.append([old_path, new_path])
                used_removed.add(old_path)
                used_added.add(new_path)
        added = [path for path in added if path not in used_added]
        removed = [path for path in removed if path not in used_removed]
        return renamed, added, removed

    def apply(self, base: str, changes: dict) -> dict:
        """用旧快照与差分还原新快照，返回路径 → [哈希, 字节数]。"""
        files = {path: list(info) for path, info in self.snapshots.get(base, {}).items()}
        for path in changes.get("removed", []):
            files.pop(path, None)
        for old_path, new_path in changes.get("renamed", []):
            info = files.pop(old_path, None)
            if info is not None:
                files[new_path] = info
        entries = changes.get("entries", {})
        for path in changes.get("modified", []):
            files[path] = list(entries[path])
        for path in changes.get("added", []):
            files[path] = list(entries[path])
        return {"files": files}

    def persist(self) -> bytes:
        """把全部快照写成带校验和的追加式日志并落盘，返回日志字节。"""
        lines = []
        for name, files in self.snapshots.items():
            record = {"op": "capture", "name": name,
                      "files": {path: [info[0], info[1]] for path, info in files.items()}}
            payload = _canonical(record)
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            lines.append(digest + " " + payload)
        blob = ("\n".join(lines) + "\n").encode("utf-8") if lines else b""
        with open(self.log_path, "wb") as handle:
            handle.write(blob)
        return blob

    def restore(self, blob: bytes = None) -> dict:
        """从日志字节（默认读落盘文件）重建快照，尾部半条记录忽略。"""
        if blob is None:
            blob = b""
            if os.path.exists(self.log_path):
                with open(self.log_path, "rb") as handle:
                    blob = handle.read()
        self.snapshots = {}
        self.log = []
        for record in self._decode_records(blob):
            if record.get("op") == "capture":
                name = record["name"]
                self.snapshots[name] = {path: tuple(info) for path, info in record["files"].items()}
                self.log.append(("capture", name))
        return self.stats()

    @staticmethod
    def _decode_records(blob: bytes) -> list:
        records = []
        for line in blob.decode("utf-8", errors="ignore").split("\n"):
            if not line.strip():
                continue
            digest, sep, payload = line.partition(" ")
            if not sep:
                break
            if hashlib.sha256(payload.encode("utf-8")).hexdigest() != digest:
                break
            try:
                records.append(json.loads(payload))
            except ValueError:
                break
        return records

    def stats(self) -> dict:
        return {"snapshots": len(self.snapshots), "files": sum(len(items) for items in self.snapshots.values())}
