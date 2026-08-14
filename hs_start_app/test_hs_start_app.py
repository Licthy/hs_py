"""Focused tests for launcher configuration and group behavior."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import hs_start_app


class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "config.json"
        self.config_patch = patch.object(hs_start_app, "config_path", return_value=self.config_file)
        self.config_patch.start()
        self.window = hs_start_app.LauncherWindow()

    def tearDown(self):
        self.window.close()
        self.config_patch.stop()
        self.temp_dir.cleanup()

    def make_program(self, name: str) -> str:
        path = Path(self.temp_dir.name) / name
        path.touch()
        return str(path)

    def test_default_groups_and_last_tab(self):
        self.assertEqual(["必起", "听歌", "游戏", "办公"], [g["name"] for g in self.window.data["groups"]])
        self.assertEqual("work", self.window._current_group_id())

    def test_required_and_current_programs_merge_and_deduplicate(self):
        shared = self.make_program("shared.exe")
        work_only = self.make_program("work.exe")
        required = self.window._group(hs_start_app.REQUIRED_GROUP_ID)
        work = self.window._group("work")
        required["programs"] = [
            {"id": "required-shared", "name": "Shared", "path": shared, "admin": False, "enabled": True}
        ]
        work["programs"] = [
            {"id": "work-shared", "name": "Shared again", "path": shared, "admin": True, "enabled": True},
            {"id": "work-only", "name": "Work", "path": work_only, "admin": True, "enabled": True},
        ]
        launched = self.window._programs_to_launch()
        self.assertEqual([shared, work_only], [program["path"] for program in launched])
        self.assertFalse(launched[0]["admin"])

    def test_add_programs_skips_duplicate_and_unsupported_file(self):
        app_path = self.make_program("music.exe")
        unsupported = self.make_program("notes.txt")
        self.window._add_program_paths([app_path, app_path, unsupported])
        programs = self.window._group("work")["programs"]
        self.assertEqual(1, len(programs))
        self.assertEqual("music", programs[0]["name"])

    def test_program_tree_order_is_saved(self):
        first = self.make_program("first.exe")
        second = self.make_program("second.exe")
        self.window._add_program_paths([first, second])
        second_item = self.window.program_tree.takeTopLevelItem(1)
        self.window.program_tree.insertTopLevelItem(0, second_item)
        self.window._sync_program_order()
        self.assertEqual([second, first], [p["path"] for p in self.window._group("work")["programs"]])

    def test_scene_list_reorders_non_required_groups(self):
        games_item = self.window.tabs.takeItem(2)
        self.window.tabs.insertItem(1, games_item)
        self.window._sync_group_order()
        self.assertEqual(["必起", "游戏", "听歌", "办公"], [g["name"] for g in self.window.data["groups"]])

    def test_required_scene_cannot_move_from_first_position(self):
        required_item = self.window.tabs.takeItem(0)
        self.window.tabs.insertItem(2, required_item)
        self.window._sync_group_order()
        self.assertEqual(hs_start_app.REQUIRED_GROUP_ID, self.window.data["groups"][0]["id"])
        self.assertEqual(hs_start_app.REQUIRED_GROUP_ID, self.window.tabs.item(0).data(hs_start_app.Qt.ItemDataRole.UserRole))

    def test_normalize_repairs_required_group_and_bad_last_tab(self):
        normalized = hs_start_app.normalize_config(
            {
                "theme": "invalid",
                "last_group_id": "missing",
                "groups": [{"id": "custom", "name": "自定义", "programs": []}],
            }
        )
        self.assertEqual(hs_start_app.REQUIRED_GROUP_ID, normalized["groups"][0]["id"])
        self.assertEqual("custom", normalized["last_group_id"])
        self.assertEqual("light", normalized["theme"])

    def test_open_config_folder_uses_config_directory(self):
        with patch.object(hs_start_app.os, "startfile", create=True) as startfile:
            self.window._open_config_folder()
        startfile.assert_called_once_with(str(self.config_file.parent))


if __name__ == "__main__":
    unittest.main()
