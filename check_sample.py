"""check_sample.py：按 sample/trees.json 走一圈，打印验收面。"""
import json
import os
import sys

from dirsnap import SnapshotStore


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("sample", "trees.json")
    with open(path, encoding="utf-8") as handle:
        spec = json.load(handle)
    store = SnapshotStore()
    for name in ("v1", "v2"):
        store.capture(name, {path_: tuple(info) for path_, info in spec[name].items()})
    changes = store.diff("v1", "v2")
    applied = store.apply("v1", changes)
    blob = store.persist()
    reborn = SnapshotStore()
    restored = reborn.restore(blob)
    print("新增 =", changes.get("added"))
    print("删除 =", changes.get("removed"))
    print("内容变化 =", changes.get("modified"))
    print("重命名对 =", changes.get("renamed"))
    print("增量传输字节 =", changes.get("transfer_bytes"))
    print("全量传输字节 =", sum(info[1] for info in spec["v2"].values()))
    print("按差分还原后与 v2 一致 =", applied.get("files") == {k: list(v) for k, v in spec["v2"].items()})
    print("恢复后的快照数 =", restored.get("snapshots"))
    print("不变量（差分只认内容，不产生多余传输） =", spec["diff_invariant"])
    print("v2 文件数 =", len(spec["v2"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
