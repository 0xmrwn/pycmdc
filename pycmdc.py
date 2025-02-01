#!/usr/bin/env python3
"""
Enhanced CLI Tool for Interactive File Selection and Content Extraction

This script allows users to browse a directory, view a beautifully rendered
tree structure of files, interactively select files, and extract their content
with clear headers and styling.
"""

import os
import fnmatch
import pyperclip
from pathlib import Path
import typer
from rich.console import Console
from rich.tree import Tree
from rich.syntax import Syntax
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from InquirerPy import inquirer
from typing import Optional, List
import toml

# Create a Typer app instance with subcommands
app = typer.Typer(
    help="Interactive CLI tool for browsing and selecting files for LLM contexts."
)

DEFAULT_CONFIG_PATH = Path.home() / ".cmdc" / "config.toml"
console = Console()


def load_config() -> dict:
    """Load configuration from file or environment variables."""
    config = {
        "filters": [],
        "ignore_patterns": [".git", "node_modules", "__pycache__", "*.pyc"],
        "recursive": False,
    }

    # Load from config file if it exists
    if DEFAULT_CONFIG_PATH.exists():
        try:
            file_config = toml.load(DEFAULT_CONFIG_PATH)
            config.update(file_config.get("cmdc", {}))
        except Exception as e:
            console.print(
                Panel(
                    f"[yellow]Warning:[/yellow] Error reading config file: {e}",
                    style="yellow",
                )
            )

    # Override with environment variables if they exist
    if os.getenv("CMDC_FILTERS"):
        config["filters"] = os.getenv("CMDC_FILTERS").split(",")
    if os.getenv("CMDC_IGNORE"):
        config["ignore_patterns"] = os.getenv("CMDC_IGNORE").split(",")
    if os.getenv("CMDC_RECURSIVE"):
        config["recursive"] = os.getenv("CMDC_RECURSIVE").lower() == "true"

    return config


def should_ignore(path: Path, ignore_patterns: List[str]) -> bool:
    """Check if a path should be ignored based on patterns."""
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(str(path), pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
    return False


def file_matches_filter(file: Path, filters: list[str]) -> bool:
    """
    Check if a file matches the provided filter extensions.
    If no filters are provided, all files are accepted.
    """
    if not filters:
        return True
    # Check if the file's suffix matches any of the provided extensions.
    return any(file.suffix == ext for ext in filters)


def get_files(
    directory: Path, recursive: bool, filters: List[str], ignore_patterns: List[str]
) -> List[Path]:
    """
    Retrieve a list of files from the directory that match the filters
    and don't match ignore patterns.
    """
    files = []
    if recursive:
        for root, _, filenames in os.walk(directory):
            root_path = Path(root)
            if should_ignore(root_path, ignore_patterns):
                continue
            for filename in filenames:
                file_path = root_path / filename
                if not should_ignore(
                    file_path, ignore_patterns
                ) and file_matches_filter(file_path, filters):
                    files.append(file_path)
    else:
        for file in directory.iterdir():
            if (
                file.is_file()
                and not should_ignore(file, ignore_patterns)
                and file_matches_filter(file, filters)
            ):
                files.append(file)
    return sorted(files)


def build_tree(
    directory: Path, recursive: bool, filters: List[str], ignore_patterns: List[str]
) -> Tree:
    """Build and return a Rich Tree representing the directory structure."""
    tree = Tree(f"[bold blue]{directory.name or str(directory)}[/bold blue]")

    if recursive:

        def add_branch(branch: Tree, path: Path):
            try:
                entries = sorted(
                    path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
                )
            except PermissionError:
                return

            for entry in entries:
                if should_ignore(entry, ignore_patterns):
                    continue

                if entry.is_dir():
                    sub_branch = Tree(f"[bold magenta]{entry.name}[/bold magenta]")
                    add_branch(sub_branch, entry)
                    if sub_branch.children:
                        branch.add(sub_branch)
                elif file_matches_filter(entry, filters):
                    branch.add(f"[green]{entry.name}[/green]")

        add_branch(tree, directory)
    else:
        try:
            for entry in sorted(
                directory.iterdir(), key=lambda p: (not p.is_file(), p.name.lower())
            ):
                if (
                    entry.is_file()
                    and not should_ignore(entry, ignore_patterns)
                    and file_matches_filter(entry, filters)
                ):
                    tree.add(f"[green]{entry.name}[/green]")
        except PermissionError:
            pass

    return tree


def clear_console():
    """Clear the console screen."""
    # For Windows
    if os.name == "nt":
        os.system("cls")
    # For Unix/Linux/MacOS
    else:
        os.system("clear")


@app.command()
def browse(
    directory: Optional[Path] = typer.Argument(
        None,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Directory to browse (default is current working directory).",
    ),
    output: str = typer.Option(
        "console",
        "--output",
        "-o",
        help="Output mode: 'console' or filename",
    ),
    filter: List[str] = typer.Option(
        None,
        "--filter",
        "-f",
        help="Filter files by extension (e.g., .py .js)",
    ),
    recursive: bool = typer.Option(
        None,
        "--recursive",
        "-r",
        help="Recursively traverse subdirectories",
    ),
    ignore: List[str] = typer.Option(
        None,
        "--ignore",
        "-i",
        help="Patterns to ignore (e.g., .git node_modules)",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Select all matching files without prompting",
    ),
    copy_to_clipboard: bool = typer.Option(
        False,
        "--copy",
        "-c",
        help="Copy output to clipboard",
    ),
):
    """Browse and select files interactively."""
    # Display a welcome banner
    banner_text = (
        "[bold cyan]Interactive File Browser & Extractor[/bold cyan]\n"
        "Browse directories, preview content, and extract files for LLM contexts."
    )
    console.print(Panel(banner_text, style="bold green", expand=False))

    # Load config and merge with command line arguments
    config = load_config()

    if directory is None:
        directory = Path.cwd()
    if filter is None:
        filter = config["filters"]
    if ignore is None:
        ignore = config["ignore_patterns"]
    if recursive is None:
        recursive = config["recursive"]

    # Scan for files with a spinner
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Scanning files...", total=None)
        files = get_files(directory, recursive, filter, ignore)

    if not files:
        console.print(
            Panel("[red]No files found matching the criteria.[/red]", title="Error")
        )
        raise typer.Exit(code=1)

    # Build and display directory tree in a panel
    tree = build_tree(directory, recursive, filter, ignore)
    console.print(
        Panel(
            tree,
            title="[bold underline]Directory Structure[/bold underline]",
            border_style="blue",
        )
    )

    # File selection
    if non_interactive:
        selected_files = [str(f.relative_to(directory)) for f in files]
    else:
        choices = [str(f.relative_to(directory)) for f in files]
        selected_files = inquirer.checkbox(
            message="Select files to extract:",
            choices=choices,
            cycle=True,
        ).execute()

    if not selected_files:
        console.print(
            Panel("[yellow]No files selected. Exiting.[/yellow]", title="Info")
        )
        raise typer.Exit(code=0)

    # Clear the console before showing file contents
    clear_console()

    # Prepare output text for non-console output
    output_text = ""
    # For console output, we will print as we go.
    if output.lower() == "console":
        console.rule("[bold green]Extracted File Contents[/bold green]")

    # Process each selected file
    for file_path_str in selected_files:
        file_path = directory / file_path_str
        try:
            content = file_path.read_text(encoding="utf-8")
            syntax = Syntax(
                content,
                file_path.suffix.lstrip("."),
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )
            if output.lower() == "console":
                console.print("\n<open_file>")
                console.print(file_path_str)
                console.print("<contents>")
                console.print(syntax)
                console.print("</contents>")
                console.print("</open_file>\n")
            else:
                # For file output or clipboard, build plain text output
                output_text += f"\n<open_file>\n{file_path_str}\n"
                output_text += f"<contents>\n{content}\n</contents>\n"
                output_text += "</open_file>\n"
        except Exception as e:
            error_msg = f"\nError reading {file_path_str}: {e}\n"
            if output.lower() == "console":
                console.print(f"[red]{error_msg}[/red]")
            else:
                output_text += error_msg

    # Handle output (clipboard or file)
    if copy_to_clipboard:
        try:
            pyperclip.copy(output_text)
            console.print(Panel("Content copied to clipboard!", style="bold green"))
        except Exception as e:
            console.print(Panel(f"Failed to copy to clipboard: {e}", style="red"))

    if output.lower() != "console":
        try:
            output_file = Path(output)
            output_file.write_text(output_text, encoding="utf-8")
            console.print(
                Panel(
                    f"File contents saved to [bold]{output_file.resolve()}[/bold]",
                    style="green",
                )
            )
        except Exception as e:
            console.print(Panel(f"Error writing to output file: {e}", style="red"))
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
