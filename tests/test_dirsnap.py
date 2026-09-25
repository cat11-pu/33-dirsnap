import unittest

from dirsnap import SnapshotStore
from diffapi import Repo


V1 = {"a": ("h1", 10), "old": ("h2", 20)}
V2 = {"a": ("h9", 12), "new": ("h2", 20), "b": ("h3", 5)}


class TestSnapshotStore(unittest.TestCase):
    def test_capture_counts(self):
        store = SnapshotStore()
        self.assertEqual(store.capture("v1", {"a": ("h1", 10)})["files"], 1)

    def test_diff_sees_added(self):
        store = SnapshotStore()
        store.capture("v1", {"a": ("h1", 10)})
        store.capture("v2", {"a": ("h1", 10), "b": ("h2", 5)})
        self.assertEqual(store.diff("v1", "v2")["added"], ["b"])

    def test_diff_sees_removed(self):
        store = SnapshotStore()
        store.capture("v1", {"a": ("h1", 10)})
        store.capture("v2", {})
        self.assertEqual(store.diff("v1", "v2")["removed"], ["a"])

    def test_stats_shape(self):
        self.assertIn("snapshots", SnapshotStore().stats())

    def test_repo_wraps_store(self):
        repo = Repo()
        repo.capture("v1", {"a": ("h1", 1)})
        self.assertEqual(repo.store.stats()["files"], 1)


class TestContentDiff(unittest.TestCase):
    def setUp(self):
        self.store = SnapshotStore()
        self.store.capture("v1", V1)
        self.store.capture("v2", V2)
        self.changes = self.store.diff("v1", "v2")

    def test_diff_sees_modified(self):
        self.assertEqual(self.changes["modified"], ["a"])

    def test_diff_pairs_rename(self):
        self.assertEqual(self.changes["renamed"], [["old", "new"]])
        self.assertEqual(self.changes["added"], ["b"])
        self.assertEqual(self.changes["removed"], [])

    def test_transfer_bytes_skip_renames(self):
        self.assertEqual(self.changes["transfer_bytes"], 12 + 5)

    def test_ambiguous_hash_not_renamed(self):
        store = SnapshotStore()
        store.capture("v1", {"x": ("h", 1), "y": ("h", 1)})
        store.capture("v2", {"z": ("h", 1)})
        changes = store.diff("v1", "v2")
        self.assertEqual(changes["renamed"], [])
        self.assertEqual(changes["added"], ["z"])
        self.assertEqual(changes["removed"], ["x", "y"])

    def test_apply_rebuilds_target(self):
        rebuilt = self.store.apply("v1", self.changes)
        self.assertEqual(rebuilt["files"], {path: list(info) for path, info in V2.items()})

    def test_transfer_never_exceeds_full(self):
        full = sum(info[1] for info in V2.values())
        self.assertLessEqual(self.changes["transfer_bytes"], full)


class TestPersistRestore(unittest.TestCase):
    def test_restore_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            store = SnapshotStore(log_path=f"{tmp}/snap.log")
            store.capture("v1", V1)
            store.capture("v2", V2)
            blob = store.persist()
            reborn = SnapshotStore(log_path=f"{tmp}/snap.log")
            self.assertEqual(reborn.restore(blob)["snapshots"], 2)
            self.assertEqual(reborn.diff("v1", "v2"), store.diff("v1", "v2"))
            self.assertEqual(reborn.restore()["snapshots"], 2)

    def test_restore_ignores_torn_tail(self):
        store = SnapshotStore()
        store.capture("v1", V1)
        store.capture("v2", V2)
        blob = store.persist()
        torn = blob + blob.split(b"\n")[0][:10]
        reborn = SnapshotStore()
        self.assertEqual(reborn.restore(torn)["snapshots"], 2)


if __name__ == "__main__":
    unittest.main()
