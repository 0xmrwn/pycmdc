from pathlib import Path
from typing import List, Iterable

import fnmatch
import os
import typer
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree

from cmdc.utils import build_directory_tree

console = Console()


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
    ):
        self.directory = directory
        self.recursive = recursive
        self.filters = filters
        self.ignore_patterns = ignore_patterns

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

    def walk_valid_paths(self) -> Iterable[Path]:
        """
        Yield valid Path objects (directories and files) that pass the ignore checks.
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
        else:
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

    def scan_and_select_files(self, non_interactive: bool) -> List[str]:
        """
        Scan the directory and prompt the user to select files (unless in non-interactive mode).
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

        tree = self.build_tree()
        console.print(
            Panel(
                tree,
                title="[bold underline]Directory Structure[/bold underline]",
                border_style="blue",
            )
        )

        # Print instructions in a separate panel
        console.print(
            Panel(
                "[bold]Keyboard Shortcuts:[/bold]\n"
                "↑/↓: Navigate • Space: Select • Enter: Confirm\n"
                "Type to Search • Ctrl+A: Select All • Ctrl+D: Toggle All",
                title="[bold]Instructions[/bold]",
                border_style="green",
            )
        )

        if non_interactive:
            selected_files = [str(f.relative_to(self.directory)) for f in files]
        else:
            # Create choices list with relative paths
            choices = [
                Choice(
                    str(f.relative_to(self.directory)),
                    name=str(f.relative_to(self.directory)),
                )
                for f in sorted(files, key=lambda x: x.name.lower())
            ]

            selected_files = inquirer.fuzzy(
                message="Select files to extract (type to search):",
                choices=choices,
                cycle=True,
                validate=lambda result: len(result) > 0,
                invalid_message="Please select at least one file",
                instruction="Use Tab to select/unselect, type to search",
                border=True,
                max_height=8,
                transformer=lambda result: f"{len(result)} file{'s' if len(result) != 1 else ''} selected",
                multiselect=True,
                info=True,
                marker="◉ ",
                marker_pl="○ ",
                keybindings={
                    "answer": [{"key": "enter"}],
                    "toggle": [{"key": "tab"}],
                    "toggle-all": [{"key": "c-a"}, {"key": "c-d"}],
                    "interrupt": [{"key": "c-c"}],
                },
            ).execute()

        if not selected_files:
            console.print(
                Panel("[yellow]No files selected. Exiting.[/yellow]", title="Info")
            )
            raise typer.Exit(code=0)

        return selected_files
