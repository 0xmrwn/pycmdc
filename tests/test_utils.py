from pathlib import Path
from unittest.mock import PropertyMock, patch

from rich.tree import Tree

from cmdc.utils import build_directory_tree, clear_console, count_tokens


def test_count_tokens_basic():
    text = "Hello, world!"
    token_count = count_tokens(text)
    assert isinstance(token_count, int)
    assert token_count > 0


def test_count_tokens_empty():
    assert count_tokens("") == 0


def test_count_tokens_special_chars():
    text = "Hello 🌍! Special chars: @#$%^&*()"
    token_count = count_tokens(text)
    assert isinstance(token_count, int)
    assert token_count > 0


def test_count_tokens_invalid_encoding():
    # Should fallback to o200k_base when invalid encoding is provided
    text = "Test text"
    token_count = count_tokens(text, encoding_name="invalid_encoding")
    assert isinstance(token_count, int)
    assert token_count > 0


@patch("os.name", "nt")
def test_clear_console_windows():
    with patch("os.system") as mock_system:
        clear_console()
        mock_system.assert_called_once_with("cls")


@patch("os.name", new_callable=PropertyMock)
def test_clear_console_unix(mock_name):
    mock_name.return_value = "posix"
    with patch("builtins.print") as mock_print:
        clear_console()
        mock_print.assert_called_once_with("\033[H\033[J", end="")


def test_build_directory_tree_basic():
    # Create a mock walk function that simulates a simple directory structure
    root = Path("/test")
    file1 = root / "file1.txt"
    file2 = root / "file2.txt"
    subdir = root / "subdir"
    subfile = subdir / "subfile.txt"

    def mock_walk():
        return [root, file1, file2, subdir, subfile]

    def mock_filter(path):
        return True

    tree = build_directory_tree(root, mock_walk, mock_filter)

    assert isinstance(tree, Tree)
    assert tree.label == "test"


def test_build_directory_tree_with_styling():
    root = Path("/test")
    file1 = root / "file1.txt"

    def mock_walk():
        return [root, file1]

    def mock_filter(path):
        return True

    def style_dir(name):
        return f"Dir: {name}"

    def style_file(name):
        return f"File: {name}"

    tree = build_directory_tree(
        root, mock_walk, mock_filter, style_directory=style_dir, style_file=style_file
    )

    assert isinstance(tree, Tree)
    assert tree.label == "Dir: test"


def test_build_directory_tree_with_filter():
    root = Path("/test")
    file1 = root / "file1.txt"
    file2 = root / "file2.py"

    def mock_walk():
        return [root, file1, file2]

    def mock_filter(path):
        return str(path).endswith(".py")

    tree = build_directory_tree(root, mock_walk, mock_filter)

    # Get all rendered lines from the tree
    rendered_lines = []

    def render_tree(t):
        rendered_lines.append(str(t.label))
        for child in t.children:
            render_tree(child)

    render_tree(tree)
    rendered_text = "\n".join(rendered_lines)

    assert "file2.py" in rendered_text
    assert "file1.txt" not in rendered_text
