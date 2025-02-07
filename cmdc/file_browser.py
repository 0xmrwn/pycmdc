import fnmatch
import os
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import typer
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.tree import Tree

from cmdc.prompt_style import get_custom_style
from cmdc.utils import build_directory_tree, count_tokens

console = Console()


class PanelProgress(Progress):
    def get_renderables(self):
        yield Panel(
            self.make_tasks_table(self.tasks),
            title="[bold]Tokenization[/bold]",
            border_style="blue",
        )


class FileBrowser:
    """
    Handles directory scanning, file filtering, and building a visual tree
    of the directory structure.
    """

    def __init__(
        self,
        directory: Path,
        recursive: bool,
        filters: List[str],
        ignore_patterns: List[str],
        depth: Optional[int] = None,
        encoding_model: str = "o200k_base",
    ):
        self.directory = directory
        self.recursive = recursive
        self.filters = filters
        self.ignore_patterns = ignore_patterns
        self.depth = depth
        self.encoding_model = encoding_model

    @staticmethod
    def _extract_relative(display_str: str) -> str:
        """
        Extract the relative path from a display string of the form "path [X tokens]".
        """
        return display_str.split(" [")[0]

    def _transform_selection(self, selected: List[str], token_counts: dict) -> str:
        """
        Transform the selection display to show file count and total token count.
        """
        if not selected:
            return "No files selected"
        total = sum(
            token_counts.get(self._extract_relative(item), 0) for item in selected
        )
        return (
            f"{len(selected)} file{'s' if len(selected) != 1 else ''} selected, "
            f"total {total} tokens"
        )

    def should_ignore(self, path: Path) -> bool:
        """
        Check if a path should be ignored based on the ignore patterns.
        """
        return any(
            fnmatch.fnmatch(part, pattern)
            for part in path.absolute().parts
            for pattern in self.ignore_patterns
        )

    def file_matches_filter(self, file: Path) -> bool:
        """
        Check if a file matches the provided filter extensions.
        If no filters are provided, all files are accepted.
        """
        if not self.filters:
            return True
        return any(file.suffix == ext for ext in self.filters)

    def _limited_walk(self, current: Path, current_level: int) -> Iterable[Path]:
        """
        Helper method for depth-limited directory traversal.
        Yields paths up to the specified depth level.
        """
        try:
            # yield only when current_level > 0.
            # When depth==1, only immediate children will be yielded.
            if current_level > 0 and not self.should_ignore(current):
                yield current
            if current.is_dir() and current_level < self.depth:
                for child in current.iterdir():
                    if self.should_ignore(child):
                        continue
                    yield from self._limited_walk(child, current_level + 1)
        except PermissionError:
            pass

    def walk_valid_paths(self) -> Iterable[Path]:
        """
        Yield valid Path objects (directories and files) that pass the ignore checks.
        If recursive mode is enabled, use full recursion via os.walk.
        Otherwise, if a depth is set, use a limited recursion approach.
        """
        if self.recursive:
            for root, dirs, filenames in os.walk(self.directory):
                root_path = Path(root)
                if self.should_ignore(root_path):
                    continue
                # Prune ignored directories
                dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]
                yield root_path
                for fname in filenames:
                    fpath = root_path / fname
                    if not self.should_ignore(fpath):
                        yield fpath
        elif self.depth is not None:
            # Use a limited depth traversal.
            yield from self._limited_walk(self.directory, 0)
        else:
            # Non-recursive mode (only immediate children)
            try:
                for item in self.directory.iterdir():
                    if not self.should_ignore(item):
                        yield item
            except PermissionError:
                pass

    def get_files(self) -> List[Path]:
        """
        Retrieve a list of files from the directory that match the filters
        and do not match the ignore patterns.
        """
        return sorted(
            [
                p
                for p in self.walk_valid_paths()
                if p.is_file() and self.file_matches_filter(p)
            ],
            key=lambda p: p.name.lower(),
        )

    def build_tree(self) -> Tree:
        """Build and return a Rich Tree representing the directory structure."""
        return build_directory_tree(
            directory=self.directory,
            walk_function=self.walk_valid_paths,
            file_filter=self.file_matches_filter,
            style_directory=lambda x: f"[bold magenta]{x}[/bold magenta]",
            style_file=lambda x: f"[green]{x}[/green]",
        )

    def scan_and_select_files(self, non_interactive: bool) -> Tuple[List[str], int]:
        """
        Scan the directory and prompt the user to select files (unless in non-interactive mode).
        Returns:
            A tuple containing:
              - List of selected file paths (relative to the root directory).
              - Total token count (integer) for the selected files.
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Scanning files...", total=None)
            files = self.get_files()

        if not files:
            console.print(
                Panel("[red]No files found matching the criteria.[/red]", title="Error")
            )
            raise typer.Exit(code=1)

        # Build a mapping: relative file path -> token count BEFORE showing the tree
        token_counts = {}
        with PanelProgress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            expand=True,
        ) as progress:
            task = progress.add_task(
                description="Computing token counts...",
                total=len(files),
            )
            for f in files:
                relative_path = str(f.relative_to(self.directory))
                try:
                    content = f.read_text(encoding="utf-8")
                    token_count = count_tokens(content, self.encoding_model)
                    token_counts[relative_path] = token_count
                except Exception:
                    token_counts[relative_path] = 0
                progress.advance(task)

        tree = self.build_tree()
        console.print(
            Panel(
                tree,
                title=(
                    "[bold underline]Directory Structure[/bold underline] "
                    + (
                        "(Recursive)"
                        if self.recursive
                        else f"(Depth: {self.depth})"
                        if self.depth
                        else "(Non-recursive)"
                    )
                ),
                border_style="blue",
            )
        )

        console.rule("[bold blue]Context Selection", style="blue", align="center")
        # Print instructions in a separate panel
        console.print(
            Panel(
                "[bold]Keyboard Shortcuts[/bold]\n"
                "↑/↓: Navigate • ←/→: Toggle • ↵: Confirm • "
                "^A: Select All • ^D: Toggle All",
                border_style="blue",
            )
        )

        style = get_custom_style()

        if non_interactive:
            selected_files = [str(f.relative_to(self.directory)) for f in files]
            total_tokens = sum(token_counts.values())
            return selected_files, total_tokens
        else:
            # Create choices with the token count appended to the file name.
            choices = [
                Choice(
                    str(relative_path),
                    name=f"{relative_path} [{token_counts.get(relative_path, 0)} tokens]",
                )
                for relative_path in sorted(
                    token_counts.keys(), key=lambda x: x.lower()
                )
            ]

            selected_files = inquirer.fuzzy(
                message="Select files to include in the context dump:",
                choices=choices,
                style=style,
                border=True,
                validate=lambda result: len(result) > 0,
                invalid_message="Please select at least one file",
                instruction="(type to search)",
                max_height=8,
                amark=" ✓ ",
                transformer=lambda selected: self._transform_selection(
                    selected, token_counts
                ),
                multiselect=True,
                info=True,
                marker=" ◉ ",
                marker_pl=" ○ ",
                keybindings={
                    "answer": [{"key": "enter"}],
                    "toggle": [{"key": "left"}, {"key": "right"}],
                    "toggle-all": [{"key": "c-a"}, {"key": "c-d"}],
                    "interrupt": [{"key": "c-c"}],
                },
                filter=lambda result: [self._extract_relative(item) for item in result],
            ).execute()

            if not selected_files:
                console.print(
                    Panel("[yellow]No files selected. Exiting.[/yellow]", title="Info")
                )
                raise typer.Exit(code=0)
            total_tokens = sum(token_counts.get(item, 0) for item in selected_files)
            return selected_files, total_tokens
