from pathlib import Path

import pyperclip
import pytest
import typer

from cmdc.output_handler import OutputHandler


def test_create_summary_section(tmp_path):
    # Create two dummy files in the temporary directory.
    (tmp_path / "file1.py").write_text("print('Hello')")
    (tmp_path / "file2.txt").write_text("Hello World")

    # Initialize the OutputHandler (no clipboard/console output needed here).
    handler = OutputHandler(
        directory=tmp_path, copy_to_clipboard=False, print_to_console=False
    )
    summary = handler.create_summary_section(["file1.py", "file2.txt"])

    # Verify that the summary string includes all expected tags and file names.
    assert "<summary>" in summary
    assert "<selected_files>" in summary
    assert "file1.py" in summary
    assert "file2.txt" in summary
    assert "<directory_structure>" in summary


def test_create_directory_tree(tmp_path):
    # Create a subdirectory with a dummy file.
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "test.txt").write_text("Test content")

    handler = OutputHandler(
        directory=tmp_path, copy_to_clipboard=False, print_to_console=False
    )
    tree = handler.create_directory_tree()

    # Check that the output tree includes the subdirectory and the file.
    assert "subdir" in tree
    assert "test.txt" in tree


def test_should_ignore(tmp_path):
    # Initialize OutputHandler and override the ignore patterns.
    handler = OutputHandler(
        directory=tmp_path, copy_to_clipboard=False, print_to_console=False
    )
    handler.ignore_patterns = ["*.log", "*ignore*"]

    p1 = Path(tmp_path / "ignored_file.txt")
    p2 = Path(tmp_path / "important.txt")
    p3 = Path(tmp_path / "error.log")

    assert handler.should_ignore(p1) is True
    assert handler.should_ignore(p2) is False
    assert handler.should_ignore(p3) is True


def test_walk_paths(tmp_path):
    # Create two files: one that should be kept and one that should be ignored.
    (tmp_path / "keep.txt").write_text("keep")
    (tmp_path / "ignore.log").write_text("ignore")

    handler = OutputHandler(
        directory=tmp_path, copy_to_clipboard=False, print_to_console=False
    )
    handler.ignore_patterns = ["*.log"]

    paths = list(handler.walk_paths())
    names = [p.name for p in paths]

    assert "keep.txt" in names
    assert "ignore.log" not in names


def test_process_output_console_clipboard(tmp_path, monkeypatch):
    # Create a dummy file.
    (tmp_path / "file1.py").write_text("print('Hello')")

    # Capture what is passed to pyperclip.copy.
    captured = {}

    def dummy_copy(text):
        captured["text"] = text

    monkeypatch.setattr(pyperclip, "copy", dummy_copy)

    handler = OutputHandler(
        directory=tmp_path, copy_to_clipboard=True, print_to_console=False
    )
    success, output_path = handler.process_output(["file1.py"], "console")

    # In console mode with clipboard enabled, we expect a successful outcome with no file path.
    assert success is True
    assert output_path is None
    # Verify that the copied text contains the file content.
    assert "print('Hello')" in captured.get("text", "")


def test_process_output_file_mode(tmp_path):
    # Create a dummy file.
    (tmp_path / "file1.py").write_text("print('Hello')")
    output_file = tmp_path / "output.txt"

    handler = OutputHandler(
        directory=tmp_path, copy_to_clipboard=False, print_to_console=False
    )
    success, output_path = handler.process_output(["file1.py"], str(output_file))

    assert success is True
    assert output_path is not None

    content = output_file.read_text(encoding="utf-8")
    # The output should contain structured sections and the file's content.
    assert "<open_file>" in content
    assert "file1.py" in content
    assert "print('Hello')" in content


def test_process_output_read_error(tmp_path, monkeypatch):
    # Create a file that will simulate a read error.
    file_path = tmp_path / "file1.py"
    file_path.write_text("print('Hello')")

    # Create a class-level patch for read_text
    original_read_text = Path.read_text

    def read_text_fail(*args, **kwargs):
        if str(args[0]).endswith("file1.py"):
            raise Exception("Simulated read error")
        return original_read_text(*args, **kwargs)

    # Patch at the class level
    monkeypatch.setattr(Path, "read_text", read_text_fail)

    output_file = tmp_path / "output.txt"
    handler = OutputHandler(
        directory=tmp_path, copy_to_clipboard=False, print_to_console=False
    )
    # Run in file mode so that the output (including error messages) is written to a file.
    success, _ = handler.process_output(["file1.py"], str(output_file))

    content = output_file.read_text(encoding="utf-8")
    # Verify that the error message is appended to the output.
    assert "Error reading" in content
    assert "Simulated read error" in content


def test_process_output_file_write_error(tmp_path, monkeypatch):
    # Create a dummy file.
    (tmp_path / "file1.py").write_text("print('Hello')")
    output_file = tmp_path / "output.txt"

    # Simulate a write error by making write_text always raise an exception.
    def write_text_fail(text, encoding="utf-8"):
        raise Exception("Simulated write error")

    monkeypatch.setattr(Path, "write_text", write_text_fail)

    handler = OutputHandler(
        directory=tmp_path, copy_to_clipboard=False, print_to_console=False
    )
    # Expect that a write error causes the process to exit.
    with pytest.raises(typer.Exit):
        handler.process_output(["file1.py"], str(output_file))
