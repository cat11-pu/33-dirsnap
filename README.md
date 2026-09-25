# dirsnap

纯 Python 标准库的 dirsnap。

## 用法

    from diffapi import Repo

    repo = Repo()
    repo.capture("v1", {"src/a.py": ("h1", 120)})   # 路径 → (内容哈希, 字节数)
    repo.capture("v2", {"src/a.py": ("h9", 150), "src/b.py": ("h2", 80)})

    changes = repo.diff("v1", "v2")
    # → {"added": [...], "removed": [...], "modified": [...],
    #    "renamed": [[old, new], ...], "transfer_bytes": N}
    # transfer_bytes 只累计新增与内容变化的字节数，重命名不计。

    repo.apply("v1", changes)        # 用旧快照 + 差分还原新快照的 files
    blob = repo.snapshot_bytes()     # 落盘
    Repo().rebuild(blob)             # 重启恢复；尾部半条记录忽略

## 测试

    python3 -m unittest discover -s tests -v

## 场景自检

    python3 check_sample.py
