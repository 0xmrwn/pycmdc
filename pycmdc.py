import fnmatch
import os
from pathlib import Path
from typing import List, Optional

import pyperclip
import toml
import typer
from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.tree import Tree

app = typer.Typer(
    help="Interactive CLI tool for browsing and selecting files for LLM contexts."
)


def get_config_dir() -> Path:
    """Get the appropriate config directory following platform conventions."""
    if os.name == "nt":  # Windows
        app_data = os.getenv("APPDATA")
        if app_data:
            return Path(app_data) / "cmdc"
        return Path.home() / "AppData" / "Roaming" / "cmdc"
    else:  # Unix-like systems
        # Follow XDG Base Directory Specification
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "cmdc"
        return Path.home() / ".config" / "cmdc"


# Update the default config path
DEFAULT_CONFIG_PATH = get_config_dir() / "config.toml"
console = Console()


def ensure_config_dir() -> None:
    """Create the config directory if it doesn't exist."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)


def get_default_ignore_patterns() -> List[str]:
    """Get the default list of ignore patterns."""
    return [
        ".git",
        "node_modules",
        "__pycache__",
        "*.pyc",
        "venv",
        ".venv",
        "env",
        ".env",
        ".idea",
        ".vscode",
        ".pytest_cache",
        "__pycache__",
        ".coverage",
        "htmlcov",
        "build",
        "dist",
        "*.egg-info",
        ".tox",
        ".mypy_cache",
    ]


def interactive_init() -> dict:
    """Run the interactive initialization process."""
    console.print(
        Panel(
            "[bold cyan]Welcome to CMDC Configuration![/bold cyan]\n"
            "Let's set up your preferences for the file browser.",
            style="bold green",
        )
    )

    # Get clipboard preference
    copy_to_clipboard = inquirer.confirm(
        message="Do you want to automatically copy selected content to clipboard?",
        default=True,
    ).execute()

    # Get recursive preference
    recursive = inquirer.confirm(
        message="Do you want to browse directories recursively by default?",
        default=False,
    ).execute()

    # Get ignore patterns
    default_patterns = get_default_ignore_patterns()
    use_default_ignores = inquirer.confirm(
        message="Would you like to use the recommended ignore patterns?",
        default=True,
    ).execute()

    if use_default_ignores:
        # Let user modify default patterns
        ignore_patterns = inquirer.checkbox(
            message="Select patterns to ignore (space to toggle, enter to confirm):",
            choices=default_patterns,
            default=default_patterns,
        ).execute()
    else:
        # Start fresh
        ignore_patterns = []

    # Allow adding custom patterns
    while inquirer.confirm(
        message="Would you like to add custom ignore patterns?",
        default=False,
    ).execute():
        pattern = inquirer.text(
            message="Enter pattern (e.g., *.log, temp/*, etc.):",
        ).execute()
        if pattern:
            ignore_patterns.append(pattern)

    # Get file filters
    use_filters = inquirer.confirm(
        message="Would you like to set default file extension filters?",
        default=False,
    ).execute()

    filters = []
    if use_filters:
        while True:
            ext = inquirer.text(
                message="Enter file extension (e.g., .py) or press enter to finish:",
            ).execute()
            if not ext:
                break
            if not ext.startswith("."):
                ext = f".{ext}"
            filters.append(ext)

    return {
        "copy_to_clipboard": copy_to_clipboard,
        "recursive": recursive,
        "ignore_patterns": ignore_patterns,
        "filters": filters,
    }


def load_config() -> dict:
    """Load configuration from file or environment variables."""
    config = {
        "filters": [],
        "ignore_patterns": get_default_ignore_patterns(),
        "recursive": False,
        "copy_to_clipboard": True,
    }

    # Check if this is first run (no config file exists)
    if not DEFAULT_CONFIG_PATH.exists():
        console.print(
            Panel(
                "[yellow]Welcome to CMDC![/yellow]\n"
                "You're running with default settings. To customize the behavior, run:\n"
                "[bold cyan]cmdc --init[/bold cyan]",
                title="Notice",
                border_style="yellow",
            )
        )

    # Load from config file if it exists
    else:
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
    """
    Check if a path should be ignored based on patterns.
    Also checks if any parent directory matches ignore patterns.
    """
    # Convert path to absolute path to ensure consistent checking
    path = path.absolute()

    # First check the direct path name against patterns
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path.name, pattern):
            return True

    # Then check each part of the path against patterns
    for part in path.parts:
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(part, pattern):
                return True

    return False


def file_matches_filter(file: Path, filters: List[str]) -> bool:
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
        for root, dirs, filenames in os.walk(directory):
            root_path = Path(root)

            # Remove ignored directories from dirs list to prevent walking into them
            dirs[:] = [
                d for d in dirs if not should_ignore(root_path / d, ignore_patterns)
            ]

            # Skip if current directory should be ignored
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
                # Get all entries and sort them (directories first, then files)
                entries = sorted(
                    path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
                )
                # Filter out ignored entries
                entries = [
                    entry
                    for entry in entries
                    if not should_ignore(entry, ignore_patterns)
                ]
            except PermissionError:
                return

            for entry in entries:
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
            entries = sorted(
                directory.iterdir(), key=lambda p: (not p.is_file(), p.name.lower())
            )
            # Filter out ignored entries
            entries = [
                entry
                for entry in entries
                if not should_ignore(entry, ignore_patterns)
                and (entry.is_dir() or file_matches_filter(entry, filters))
            ]
            for entry in entries:
                if entry.is_file():
                    tree.add(f"[green]{entry.name}[/green]")
        except PermissionError:
            pass

    return tree


def clear_console():
    """Clear the console screen in a cross-platform way."""
    if os.name == "nt":  # For Windows
        os.system("cls")
    else:  # For Unix/Linux/MacOS
        # Using ANSI escape codes for a more elegant clear
        print("\033[H\033[J", end="")


@app.command()
def main(
    init: bool = typer.Option(
        False,
        "--init",
        help="Run interactive configuration initialization.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force reinitialization even if a configuration exists.",
    ),
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
        help="Output mode: 'console' or a filename to save the extracted content.",
    ),
    filter: Optional[List[str]] = typer.Option(
        None,
        "--filter",
        "-f",
        help="Filter files by extension (e.g., .py .js).",
    ),
    recursive: Optional[bool] = typer.Option(
        None,
        "--recursive",
        "-r",
        help="Recursively traverse subdirectories.",
    ),
    ignore: Optional[List[str]] = typer.Option(
        None,
        "--ignore",
        "-i",
        help="Additional patterns to ignore (e.g., .git node_modules).",
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Select all matching files without prompting.",
    ),
):
    """
    Interactive CLI tool for browsing and selecting files for LLM contexts.

    By default, running `cmdc` will browse the current directory. Use the options
    to modify the behavior. To run the configuration initialization, use the `--init`
    flag (with `--force` to override an existing configuration).
    """
    # If the init flag is set, perform the interactive configuration process
    if init:
        if DEFAULT_CONFIG_PATH.exists() and not force:
            overwrite = inquirer.confirm(
                message="Configuration file already exists. Do you want to overwrite it?",
                default=False,
            ).execute()
            if not overwrite:
                console.print("[yellow]Configuration unchanged.[/yellow]")
                raise typer.Exit()
        ensure_config_dir()
        config_data = interactive_init()
        try:
            with open(DEFAULT_CONFIG_PATH, "w") as f:
                toml.dump({"cmdc": config_data}, f)
            console.print(
                Panel(
                    f"[green]Configuration saved successfully to:[/green]\n{DEFAULT_CONFIG_PATH}",
                    title="Success",
                )
            )
        except Exception as e:
            console.print(
                Panel(
                    f"[red]Error saving configuration:[/red]\n{str(e)}", title="Error"
                )
            )
            raise typer.Exit(1)
        raise typer.Exit()

    # --- Browse / Extract Files Process ---
    clear_console()
    banner_text = (
        "[bold cyan]Interactive File Browser & Extractor[/bold cyan]\n"
        "Browse directories, preview content, and extract files for LLM contexts."
    )
    console.print(Panel(banner_text, style="bold green", expand=False))

    # Load configuration (and merge with environment variables)
    config = load_config()

    # Set defaults from config if not provided as command-line arguments
    if directory is None:
        directory = Path.cwd()
    if filter is None:
        filter = config["filters"]
    if ignore is None:
        ignore = config["ignore_patterns"]
    else:
        ignore = config["ignore_patterns"] + list(ignore)
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
    console.print("\n")  # Blank line for spacing

    # Prepare output text
    output_text = ""
    if output.lower() == "console":
        console.print(
            Panel("[bold green]Extracted File Contents[/bold green]", expand=False)
        )

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
            # Append file content to output_text in a marked-up format
            output_text += f"\n<open_file>\n{file_path_str}\n"
            output_text += f"<contents>\n{content}\n</contents>\n"
            output_text += "</open_file>\n"

            if output.lower() == "console":
                console.print("\n<open_file>")
                console.print(file_path_str)
                console.print("<contents>")
                console.print(syntax)
                console.print("</contents>")
                console.print("</open_file>\n")
        except Exception as e:
            error_msg = f"\nError reading {file_path_str}: {e}\n"
            if output.lower() == "console":
                console.print(f"[red]{error_msg}[/red]")
            else:
                output_text += error_msg

    # If output is to the console and clipboard copying is enabled, copy the content
    if output.lower() == "console" and config.get("copy_to_clipboard", True):
        try:
            pyperclip.copy(output_text)
            console.print(
                Panel("Content copied to clipboard successfully", style="bold green")
            )
        except Exception as e:
            console.print(Panel(f"Failed to copy to clipboard: {e}", style="red"))

    # If output is a filename, save the extracted text to the file
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
