import os
import unittest
from uuid import uuid4

from app.repositories.memory import InMemoryTaskRepository
from app.repositories.postgres import PostgresTaskRepository
from app.service import InvalidTitle, TaskNotFound, TaskService


class RepositoryContract:
    def setUp(self):
        self.repository = self.make_repository()
        self.service = TaskService(self.repository)

    def create(self, title=None):
        task = self.service.create(title or f"contract-{uuid4()}")
        self.addCleanup(self.repository.delete, task["id"])
        return task

    def test_create_get_list_and_delete(self):
        task = self.create()
        self.assertIs(type(task["done"]), bool)
        self.assertFalse(task["done"])
        self.assertEqual(self.service.get(task["id"]), task)
        self.assertIn(task, self.service.list())
        self.service.delete(task["id"])
        with self.assertRaises(TaskNotFound):
            self.service.get(task["id"])

    def test_partial_updates_preserve_other_fields_and_accept_false(self):
        task = self.create()
        task_id = task["id"]
        self.assertTrue(self.service.update(task_id, None, True)["done"])
        renamed = self.service.update(task_id, "renamed", None)
        self.assertEqual(renamed["title"], "renamed")
        self.assertTrue(renamed["done"])
        self.assertFalse(self.service.update(task_id, None, False)["done"])
        self.assertEqual(self.service.update(task_id, None, None), self.service.get(task_id))

    def test_missing_tasks(self):
        self.assertIsNone(self.repository.get(-1))
        self.assertIsNone(self.repository.update(-1, "missing", True))
        self.assertFalse(self.repository.delete(-1))
        with self.assertRaises(TaskNotFound):
            self.service.get(-1)
        with self.assertRaises(TaskNotFound):
            self.service.update(-1, "missing", True)
        with self.assertRaises(TaskNotFound):
            self.service.delete(-1)

    def test_blank_titles_are_rejected_without_changing_stored_data(self):
        for title in ("", " ", "\n\t"):
            with self.subTest(title=title), self.assertRaises(InvalidTitle):
                self.service.create(title)
        task = self.create()
        with self.assertRaises(InvalidTitle):
            self.service.update(task["id"], "  ", True)
        self.assertEqual(self.service.get(task["id"]), task)

    def test_sql_punctuation_and_unicode_are_plain_data(self):
        title = "O'Reilly; DROP TABLE tasks; -- \u4efb\u52a1"
        task = self.create(title)
        self.assertEqual(self.service.get(task["id"])["title"], title)
        self.assertIn(task, self.service.list())

    def test_results_cannot_mutate_stored_data(self):
        task = self.create()
        original = task.copy()
        task["title"] = "mutated"
        self.service.get(task["id"])["done"] = True
        for listed in self.service.list():
            if listed["id"] == task["id"]:
                listed["title"] = "mutated again"
        self.assertEqual(self.service.get(task["id"]), original)

    def test_list_is_ordered_by_id(self):
        first, second = self.create(), self.create()
        task_ids = [task["id"] for task in self.service.list()]
        self.assertEqual(task_ids, sorted(task_ids))
        self.assertLess(task_ids.index(first["id"]), task_ids.index(second["id"]))


class InMemoryRepositoryTests(RepositoryContract, unittest.TestCase):
    def make_repository(self):
        return InMemoryTaskRepository()


@unittest.skipUnless(os.getenv("RUN_POSTGRES_TESTS") == "1", "Set RUN_POSTGRES_TESTS=1")
class PostgresRepositoryTests(RepositoryContract, unittest.TestCase):
    def make_repository(self):
        return PostgresTaskRepository()

    def test_new_repository_instance_reads_committed_data(self):
        task = self.create()
        self.assertEqual(PostgresTaskRepository().get(task["id"]), task)
