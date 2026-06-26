import importlib
import os
import sys
import types
import unittest
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class _FakeCTk:
    pass


def _install_customtkinter_stub():
    module = types.ModuleType("customtkinter")
    module.CTk = _FakeCTk
    module.CTkToplevel = object
    module.CTkFrame = object
    module.CTkLabel = object
    module.CTkEntry = object
    module.CTkButton = object
    module.CTkOptionMenu = object
    module.CTkProgressBar = object
    module.CTkScrollableFrame = object
    module.CTkFont = lambda *args, **kwargs: None
    module.StringVar = lambda *args, **kwargs: None
    module.set_appearance_mode = lambda *args, **kwargs: None
    module.set_default_color_theme = lambda *args, **kwargs: None
    sys.modules.setdefault("customtkinter", module)


_install_customtkinter_stub()
file_sort = importlib.import_module("file_sort")


class FileSortCoreTests(unittest.TestCase):
    def test_chinese_labels_are_readable(self):
        self.assertEqual(file_sort.get_folder_name(".jpg"), "图片")
        self.assertEqual(file_sort.SortMode.BY_TYPE.display_name(), "按文件类型")
        self.assertEqual(file_sort.SortMode.from_display("按月份"), file_sort.SortMode.BY_MONTH)

    def test_month_folder_name_and_category_detection_match(self):
        with patch("file_sort.datetime") as fake_datetime:
            fake_datetime.fromtimestamp.return_value.strftime.return_value = "2026年05月"
            folder_name = file_sort.get_month_folder_name(0)

        self.assertEqual(folder_name, "2026年05月")

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing_month = root / folder_name
            existing_month.mkdir()
            (existing_month / "already.txt").write_text("old", encoding="utf-8")
            new_file = root / "new.txt"
            new_file.write_text("new", encoding="utf-8")
            os_time = time.mktime((2026, 5, 20, 12, 0, 0, 0, 0, -1))
            os.utime(new_file, (os_time, os_time))

            moved, _, counts = file_sort.sort_files(
                str(root),
                lambda _message: None,
                lambda _progress: None,
                [],
                file_sort.SortMode.BY_MONTH,
                [],
            )

        self.assertEqual(moved, 1)
        self.assertEqual(counts, {"2026年05月": 1})

    def test_preview_matches_files_that_sort_will_move(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            pictures = root / "图片"
            pictures.mkdir()
            (pictures / "already.jpg").write_text("old", encoding="utf-8")
            (root / "new.jpg").write_text("new", encoding="utf-8")

            self.assertEqual(file_sort.preview_categories(str(root), []), {"图片": 1})

    def test_search_cache_sees_new_files_under_root(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "old.txt").write_text("old", encoding="utf-8")
            self.assertEqual([item["name"] for item in file_sort.FileSearcher.search(str(root), "old")], ["old.txt"])

            (root / "new.txt").write_text("new", encoding="utf-8")
            self.assertEqual([item["name"] for item in file_sort.FileSearcher.search(str(root), "new")], ["new.txt"])

    def test_search_cache_sees_new_files_inside_existing_subdirectories(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "child"
            child.mkdir()
            (child / "old.txt").write_text("old", encoding="utf-8")
            self.assertEqual([item["name"] for item in file_sort.FileSearcher.search(str(root), "old")], ["old.txt"])

            (child / "new.txt").write_text("new", encoding="utf-8")
            self.assertEqual([item["name"] for item in file_sort.FileSearcher.search(str(root), "new")], ["new.txt"])


if __name__ == "__main__":
    unittest.main()
