import fnmatch
from pathlib import Path
from typing import List, Iterable

import pyperclip
import typer
from rich.console import Console
from rich.panel import Panel


console = Console()


class OutputHandler:
    """
    Handles processing and outputting the content of selected files.
    The output can be directed to the console (with optional clipboard copy)
    or saved to a specified file.
    """

    def __init__(
        self,
        directory: Path,
        copy_to_clipboard: bool,
        print_to_console: bool = False,
        ignore_patterns: List[str] = None,
    ):
        self.directory = directory
        self.copy_to_clipboard = copy_to_clipboard
        self.print_to_console = print_to_console
        self.ignore_patterns = ignore_patterns or []

    def should_ignore(self, path: Path) -> bool:
        """
        Check if a path should be ignored based on the ignore patterns.
        For filename-only patterns (like *.log), check only against the filename.
        For directory-like patterns (those without * or ? wildcards), check against full path.
        """
        # For each pattern, determine how to apply it
        for pattern in self.ignore_patterns:
            # Simple filename pattern with wildcard (like *.log, *ignore*)
            if "*" in pattern or "?" in pattern:
                if fnmatch.fnmatch(path.name, pattern):
                    return True
            # Directory/path-based pattern (like node_modules, .git)
            else:
                if any(part == pattern for part in path.absolute().parts):
                    return True
        return False

    def walk_paths(self) -> Iterable[Path]:
        """Walk through directory yielding paths that aren't ignored."""
        for path in self.directory.rglob("*"):
            if not self.should_ignore(path):
                yield path

    def create_directory_tree(self) -> str:
        """Create an XML representation of the directory tree."""
        xml_output = '<?xml version="1.0" encoding="UTF-8"?>\n<tree>\n'

        # Start with the root directory
        xml_output += f'  <directory name="{self.directory.name}">\n'

        # Build directory structure recursively
        def build_xml_tree(directory, indent="    "):
            nonlocal xml_output

            # Sort entries: directories first, then files
            try:
                entries = sorted(
                    [p for p in directory.iterdir() if not self.should_ignore(p)],
                    key=lambda p: (not p.is_dir(), p.name.lower()),
                )
            except PermissionError:
                # Skip directories we don't have permission to read
                return

            for entry in entries:
                if entry.is_dir():
                    xml_output += f'{indent}<directory name="{entry.name}">\n'
                    build_xml_tree(entry, indent + "  ")
                    xml_output += f"{indent}</directory>\n"
                else:
                    # Check if it's a file (and not a symlink, etc.)
                    if entry.is_file():
                        xml_output += f'{indent}<file name="{entry.name}"/>\n'

        build_xml_tree(self.directory)
        xml_output += "  </directory>\n</tree>"

        return xml_output

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
        # 1. Generate summary FIRST
        summary_content = self.create_summary_section(selected_files)

        # 2. Generate file contents separately
        files_content_builder = []
        for file_path_str in selected_files:
            file_path = self.directory / file_path_str
            try:
                content = file_path.read_text(encoding="utf-8")
                files_content_builder.append(f"\n<open_file>\n{file_path_str}\n")
                files_content_builder.append(f"<contents>\n{content}\n</contents>\n")
                files_content_builder.append("</open_file>\n")
            except Exception as e:
                error_msg = f"\nError reading {file_path_str}: {e}\n"
                files_content_builder.append(error_msg)  # Append errors too
        files_content = "".join(files_content_builder)

        # 3. Combine them for final output
        output_text = summary_content + files_content

        # 4. Handle console printing
        if self.print_to_console:
            console.print(Panel("[bold green]Summary[/bold green]", expand=False))
            # Print XML summary directly to console
            console.print(summary_content)
            console.print(
                Panel("[bold green]Extracted File Contents[/bold green]", expand=False)
            )
            # Print raw file contents string to console
            # Per-file syntax highlighting is lost here, but ensures clipboard correctness.
            # We could re-introduce syntax highlighting by looping again, but let's prioritize clipboard.
            console.print(files_content)

        # 5. Handle clipboard
        if output_mode.lower() == "console" and self.copy_to_clipboard:
            try:
                pyperclip.copy(output_text)  # Copy the combined text
                return True, None  # Success with no file path
            except Exception as e:
                console.print(Panel(f"Failed to copy to clipboard: {e}", style="red"))
                return False, None

        # 6. Handle file output
        if output_mode.lower() != "console":
            try:
                output_file = Path(output_mode)
                output_file.write_text(
                    output_text, encoding="utf-8"
                )  # Write combined text
                return True, str(output_file.resolve())  # Success with file path
            except Exception as e:
                console.print(Panel(f"Error writing to output file: {e}", style="red"))
                raise typer.Exit(code=1)

        return True, None  # Default success case
