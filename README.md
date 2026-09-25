# dirsnap

纯 Python 标准库的 dirsnap。

## 用法

```python
from diffapi import Repo

repo = Repo()
repo.capture("v1", {"src/a.py": ("h1", 120)})   # 路径 → (内容哈希, 字节数)
repo.capture("v2", {"src/b.py": ("h1", 120)})
changes = repo.diff("v1", "v2")
# {"added": [], "removed": [], "modified": [],
#  "renamed": [["src/a.py", "src/b.py"]],       # 哈希在两侧各自唯一才配对
#  "transfer_bytes": 0,                          # 只算新增 + 内容变化，改名不计
#  "entries": {}}                                # 新增/修改路径的 [哈希, 字节数]
repo.apply("v1", changes)                        # 旧快照 + 差分 → 新快照
blob = repo.snapshot_bytes()                     # 落盘 dirsnap.log 并返回字节
repo.rebuild(blob)                               # 恢复；尾部半条记录自动忽略
```

## 测试

    python3 -m unittest discover -s tests -v

## 场景自检

    python3 check_sample.py
