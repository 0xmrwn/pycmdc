from pathlib import Path

import pytest

from cmdc.file_browser import FileBrowser
from cmdc.utils import count_tokens


# Fixture to create a temporary directory structure with files.
@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    # Create a temporary directory "test_dir"
    d = tmp_path / "test_dir"
    d.mkdir()
    # Create files in the root directory
    (d / "a.py").write_text("print('Hello from a')")
    (d / "b.txt").write_text("This is a text file")
    (d / "ignore.log").write_text("This file should be ignored")
    # Create a subdirectory with a file inside it
    subdir = d / "subdir"
    subdir.mkdir()
    (subdir / "c.py").write_text("print('Hello from c')")
    return d


def test_get_files_non_recursive(temp_dir: Path):
    """
    Test that get_files() returns only files in the root directory
    that match the filter (.py) and are not ignored.
    """
    fb = FileBrowser(
        directory=temp_dir,
        recursive=False,
        filters=[".py"],
        ignore_patterns=["ignore.*"],  # ignore files like ignore.log
        depth=None,
        encoding_model="o200k_base",
    )
    files = fb.get_files()
    # Non-recursive should only see a.py (b.txt is filtered out because it's not .py,
    # ignore.log is ignored, and subdir is not processed)
    file_names = [f.name for f in files]
    assert file_names == ["a.py"]


def test_get_files_recursive(temp_dir: Path):
    """
    Test that recursive mode returns files from subdirectories as well.
    """
    fb = FileBrowser(
        directory=temp_dir,
        recursive=True,
        filters=[".py"],
        ignore_patterns=["ignore.*"],
        depth=None,
        encoding_model="o200k_base",
    )
    files = fb.get_files()
    # Expect to see a.py from the root and c.py from the subdirectory.
    relative_files = sorted([str(f.relative_to(temp_dir)) for f in files])
    assert relative_files == ["a.py", "subdir/c.py"]


def test_scan_and_select_files_non_interactive(temp_dir: Path):
    """
    Test scan_and_select_files in non-interactive mode.
    It should automatically select all files matching filters.
    """
    fb = FileBrowser(
        directory=temp_dir,
        recursive=True,
        filters=[".py"],
        ignore_patterns=["ignore.*"],
        depth=None,
        encoding_model="o200k_base",
    )
    selected_files, total_tokens = fb.scan_and_select_files(non_interactive=True)
    # Expect both a.py and subdir/c.py to be returned.
    expected_files = sorted(["a.py", "subdir/c.py"])
    assert sorted(selected_files) == expected_files
    # Verify that token count is computed (should be > 0 if the file is non-empty)
    assert total_tokens > 0


def test_scan_and_select_files_interactive(monkeypatch, temp_dir: Path):
    """
    Test the interactive flow by monkeypatching InquirerPy.fuzzy.
    Here we simulate a user selecting just one file ("a.py").
    """

    # Create a fake fuzzy prompt that returns a predetermined selection.
    def fake_fuzzy(*args, **kwargs):
        class FakePrompt:
            def execute(self):
                # Simulate the user selecting "a.py"
                return ["a.py"]

        return FakePrompt()

    # Monkeypatch the inquirer.fuzzy method used in FileBrowser.
    monkeypatch.setattr("cmdc.file_browser.inquirer.fuzzy", fake_fuzzy)

    fb = FileBrowser(
        directory=temp_dir,
        recursive=True,
        filters=[".py"],
        ignore_patterns=["ignore.*"],
        depth=None,
        encoding_model="o200k_base",
    )
    selected_files, total_tokens = fb.scan_and_select_files(non_interactive=False)
    # Since we simulated selection of "a.py", assert that is what is returned.
    assert selected_files == ["a.py"]

    # Check token count. We compute what we expect for "a.py"
    a_py_path = temp_dir / "a.py"
    expected_tokens = count_tokens(a_py_path.read_text(encoding="utf-8"), "o200k_base")
    # In a simple test scenario, the total tokens should match the a.py file tokens.
    assert total_tokens == expected_tokens
