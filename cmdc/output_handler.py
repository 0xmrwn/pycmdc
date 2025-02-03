from pathlib import Path
from typing import List, Iterable
from io import StringIO
import fnmatch

import pyperclip
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from cmdc.utils import build_directory_tree
from cmdc.config_manager import ConfigManager

console = Console()


class OutputHandler:
    """
    Handles processing and outputting the content of selected files.
    The output can be directed to the console (with optional clipboard copy)
    or saved to a specified file.
    """

    def __init__(
        self, directory: Path, copy_to_clipboard: bool, print_to_console: bool = False
    ):
        self.directory = directory
        self.copy_to_clipboard = copy_to_clipboard
        self.print_to_console = print_to_console
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.ignore_patterns = self.config.get("ignore_patterns", [])

    def should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored based on the ignore patterns."""
        return any(
            fnmatch.fnmatch(part, pattern)
            for part in path.absolute().parts
            for pattern in self.ignore_patterns
        )

    def walk_paths(self) -> Iterable[Path]:
        """Walk through directory yielding paths that aren't ignored."""
        for path in self.directory.rglob("*"):
            if not self.should_ignore(path):
                yield path

    def create_directory_tree(self) -> str:
        """Create a text representation of the directory tree."""
        # Create a string buffer console to capture the tree output without colors
        string_console = Console(file=StringIO(), force_terminal=False, no_color=True)

        # Build the tree with no styling (plain text)
        tree = build_directory_tree(
            directory=self.directory,
            walk_function=self.walk_paths,
            file_filter=lambda _: True,  # Include all files that weren't ignored
        )

        string_console.print(tree)
        return string_console.file.getvalue().rstrip()

    def create_summary_section(self, selected_files: List[str]) -> str:
        """Create a summary section with the list of files and directory tree."""
        summary = "<summary>\n"

        # Add list of selected files
        summary += "<selected_files>\n"
        for file_path in sorted(selected_files):
            summary += f"{file_path}\n"
        summary += "</selected_files>\n"

        # Add directory structure
        summary += "<directory_structure>\n"
        tree_str = self.create_directory_tree()
        summary += tree_str + "\n"
        summary += "</directory_structure>\n"

        summary += "</summary>\n"
        return summary

    def process_output(self, selected_files: List[str], output_mode: str) -> tuple:
        """
        Process and output the selected files' contents.
        """
        output_text = self.create_summary_section(selected_files)

        # Simply use the print_to_console setting that was determined by the CLI
        if self.print_to_console:
            console.print(
                Panel("[bold green]Extracted File Contents[/bold green]", expand=False)
            )
            console.print(output_text)

        for file_path_str in selected_files:
            file_path = self.directory / file_path_str
            try:
                content = file_path.read_text(encoding="utf-8")
                # Always add to output_text for clipboard/file
                output_text += f"\n<open_file>\n{file_path_str}\n"
                output_text += f"<contents>\n{content}\n</contents>\n"
                output_text += "</open_file>\n"

                # Only print to console if enabled
                if self.print_to_console:
                    syntax = Syntax(
                        content,
                        file_path.suffix.lstrip("."),
                        theme="monokai",
                        line_numbers=False,
                        word_wrap=True,
                    )
                    console.print("\n<open_file>")
                    console.print(file_path_str)
                    console.print("<contents>")
                    console.print(syntax)
                    console.print("</contents>")
                    console.print("</open_file>\n")
            except Exception as e:
                error_msg = f"\nError reading {file_path_str}: {e}\n"
                output_text += error_msg
                if self.print_to_console:
                    console.print(f"[red]{error_msg}[/red]")

        if output_mode.lower() == "console" and self.copy_to_clipboard:
            try:
                pyperclip.copy(output_text)
                return True, None  # Success with no file path
            except Exception as e:
                console.print(Panel(f"Failed to copy to clipboard: {e}", style="red"))
                return False, None

        if output_mode.lower() != "console":
            try:
                output_file = Path(output_mode)
                output_file.write_text(output_text, encoding="utf-8")
                return True, str(output_file.resolve())  # Success with file path
            except Exception as e:
                console.print(Panel(f"Error writing to output file: {e}", style="red"))
                raise typer.Exit(code=1)

        return True, None  # Default success case
