import unittest

from dirsnap import SnapshotStore
from diffapi import Repo


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


if __name__ == "__main__":
    unittest.main()
