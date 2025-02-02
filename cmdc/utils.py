import os
from pathlib import Path
from typing import Dict, List, Callable, Iterable
from rich.tree import Tree


def clear_console() -> None:
    """Clear the console screen in a cross-platform way."""
    if os.name == "nt":
        os.system("cls")
    else:
        print("\033[H\033[J", end="")


def build_directory_tree(
    directory: Path,
    walk_function: Callable[[], Iterable[Path]],
    file_filter: Callable[[Path], bool],
    style_directory: Callable[[str], str] = lambda x: x,
    style_file: Callable[[str], str] = lambda x: x,
) -> Tree:
    """
    Build a Rich Tree representing a directory structure.

    Args:
        directory: Root directory Path
        walk_function: Function that yields valid Path objects
        file_filter: Function that returns True if a file should be included
        style_directory: Function to style directory names (default: no styling)
        style_file: Function to style file names (default: no styling)

    Returns:
        Rich Tree object representing the directory structure
    """
    tree = Tree(style_directory(directory.name or str(directory)))

    # Get all valid paths from the walk function
    valid_paths = list(walk_function())

    # Create a mapping of parent directories to their children
    paths_by_parent: Dict[Path, List[Path]] = {}
    for path in valid_paths:
        if path == directory:
            continue
        parent = path.parent
        if parent not in paths_by_parent:
            paths_by_parent[parent] = []
        paths_by_parent[parent].append(path)

    def add_to_tree(current_dir: Path, current_tree: Tree) -> None:
        """Recursively add paths to the tree."""
        if current_dir not in paths_by_parent:
            return

        # Sort paths: directories first, then files
        paths = sorted(
            paths_by_parent[current_dir],
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )

        for path in paths:
            if path.is_dir():
                # Only add directories that are in our valid paths
                if path in paths_by_parent or path in valid_paths:
                    sub_tree = current_tree.add(style_directory(path.name))
                    add_to_tree(path, sub_tree)
            elif file_filter(path):
                current_tree.add(style_file(path.name))

    add_to_tree(directory, tree)
    return tree
