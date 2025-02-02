import fnmatch
import os
from pathlib import Path
from typing import List, Optional, Iterable, Dict

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


def get_default_config() -> dict:
    """Get the default configuration."""
    return {
        "filters": [],
        "ignore_patterns": get_default_ignore_patterns(),
        "recursive": False,
        "copy_to_clipboard": True,
    }


def get_file_config() -> dict:
    """Load configuration from file."""
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
        return {}

    try:
        file_config = toml.load(DEFAULT_CONFIG_PATH)
        return file_config.get("cmdc", {})
    except Exception as e:
        console.print(
            Panel(
                f"[yellow]Warning:[/yellow] Error reading config file: {e}",
                style="yellow",
            )
        )
        return {}


def get_env_config() -> dict:
    """Load configuration from environment variables."""
    env_config = {}

    if os.getenv("CMDC_FILTERS"):
        env_config["filters"] = os.getenv("CMDC_FILTERS").split(",")
    if os.getenv("CMDC_IGNORE"):
        env_config["ignore_patterns"] = os.getenv("CMDC_IGNORE").split(",")
    if os.getenv("CMDC_RECURSIVE"):
        env_config["recursive"] = os.getenv("CMDC_RECURSIVE").lower() == "true"
    if os.getenv("CMDC_COPY_CLIPBOARD"):
        env_config["copy_to_clipboard"] = (
            os.getenv("CMDC_COPY_CLIPBOARD").lower() == "true"
        )

    return env_config


def load_config() -> dict:
    """
    Load configuration using a layered approach:
    1. Start with defaults
    2. Update with file config
    3. Update with environment variables
    """
    # Start with default configuration
    config = get_default_config()

    # Layer 2: File configuration
    config.update(get_file_config())

    # Layer 3: Environment variables
    config.update(get_env_config())

    return config


def should_ignore(path: Path, ignore_patterns: List[str]) -> bool:
    """
    Check if a path should be ignored based on patterns.
    Simplified version that checks all path parts against all patterns at once.
    """
    return any(
        fnmatch.fnmatch(part, pattern)
        for part in path.absolute().parts
        for pattern in ignore_patterns
    )


def file_matches_filter(file: Path, filters: List[str]) -> bool:
    """
    Check if a file matches the provided filter extensions.
    If no filters are provided, all files are accepted.
    """
    if not filters:
        return True
    # Check if the file's suffix matches any of the provided extensions.
    return any(file.suffix == ext for ext in filters)


def walk_valid_paths(
    directory: Path, recursive: bool, ignore_patterns: List[str], filters: List[str]
) -> Iterable[Path]:
    """
    Yields valid Path objects (dirs and files) that pass ignore checks.
    This is a common helper used by both get_files() and build_tree().
    """
    if recursive:
        for root, dirs, filenames in os.walk(directory):
            root_path = Path(root)

            # Skip if the root itself should be ignored
            if should_ignore(root_path, ignore_patterns):
                continue

            # Prune ignored dirs to prevent walking into them
            dirs[:] = [
                d for d in dirs if not should_ignore(root_path / d, ignore_patterns)
            ]

            # First yield the root directory itself if it's valid
            yield root_path

            # Then yield all valid files in this directory
            for fname in filenames:
                fpath = root_path / fname
                if not should_ignore(fpath, ignore_patterns):
                    yield fpath
    else:
        # For non-recursive mode, just yield immediate children
        try:
            for item in directory.iterdir():
                if not should_ignore(item, ignore_patterns):
                    yield item
        except PermissionError:
            pass


def get_files(
    directory: Path, recursive: bool, filters: List[str], ignore_patterns: List[str]
) -> List[Path]:
    """
    Retrieve a list of files from the directory that match the filters
    and don't match ignore patterns. Uses the common walk_valid_paths helper.
    """
    return sorted(
        [
            p
            for p in walk_valid_paths(directory, recursive, ignore_patterns, filters)
            if p.is_file() and file_matches_filter(p, filters)
        ],
        key=lambda p: p.name.lower(),
    )


def build_tree(
    directory: Path, recursive: bool, filters: List[str], ignore_patterns: List[str]
) -> Tree:
    """Build and return a Rich Tree representing the directory structure."""
    tree = Tree(f"[bold blue]{directory.name or str(directory)}[/bold blue]")

    # Get all valid paths and organize them by parent directory
    paths_by_parent: Dict[Path, List[Path]] = {}
    for path in walk_valid_paths(directory, recursive, ignore_patterns, filters):
        if path == directory:
            continue
        parent = path.parent
        if parent not in paths_by_parent:
            paths_by_parent[parent] = []
        paths_by_parent[parent].append(path)

    def add_to_tree(current_dir: Path, current_tree: Tree) -> None:
        """Recursively add paths to the tree structure."""
        if current_dir not in paths_by_parent:
            return

        # Sort paths: directories first, then files
        paths = sorted(
            paths_by_parent[current_dir], key=lambda p: (not p.is_dir(), p.name.lower())
        )

        for path in paths:
            if path.is_dir():
                # Add directory and recursively process its contents
                sub_tree = current_tree.add(f"[bold magenta]{path.name}[/bold magenta]")
                add_to_tree(path, sub_tree)
            elif file_matches_filter(path, filters):
                # Add file if it matches filters
                current_tree.add(f"[green]{path.name}[/green]")

    # Start building the tree from the root directory
    add_to_tree(directory, tree)
    return tree


def clear_console():
    """Clear the console screen in a cross-platform way."""
    if os.name == "nt":  # For Windows
        os.system("cls")
    else:  # For Unix/Linux/MacOS
        # Using ANSI escape codes for a more elegant clear
        print("\033[H\033[J", end="")


def handle_init(force: bool) -> None:
    """Handle the initialization process."""
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
            Panel(f"[red]Error saving configuration:[/red]\n{str(e)}", title="Error")
        )
        raise typer.Exit(1)


def scan_and_select_files(
    directory: Path,
    recursive: bool,
    filters: List[str],
    ignore_patterns: List[str],
    non_interactive: bool,
) -> List[str]:
    """Scan directory and handle file selection."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Scanning files...", total=None)
        files = get_files(directory, recursive, filters, ignore_patterns)

    if not files:
        console.print(
            Panel("[red]No files found matching the criteria.[/red]", title="Error")
        )
        raise typer.Exit(code=1)

    # Build and display directory tree
    tree = build_tree(directory, recursive, filters, ignore_patterns)
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

    return selected_files


def process_output(
    selected_files: List[str],
    directory: Path,
    output_mode: str,
    copy_to_clipboard: bool,
) -> None:
    """Process and output the selected files' contents."""
    output_text = ""
    if output_mode.lower() == "console":
        console.print(
            Panel("[bold green]Extracted File Contents[/bold green]", expand=False)
        )

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

            if output_mode.lower() == "console":
                console.print("\n<open_file>")
                console.print(file_path_str)
                console.print("<contents>")
                console.print(syntax)
                console.print("</contents>")
                console.print("</open_file>\n")
        except Exception as e:
            error_msg = f"\nError reading {file_path_str}: {e}\n"
            if output_mode.lower() == "console":
                console.print(f"[red]{error_msg}[/red]")
            else:
                output_text += error_msg

    # Handle clipboard copy if needed
    if output_mode.lower() == "console" and copy_to_clipboard:
        try:
            pyperclip.copy(output_text)
            console.print(
                Panel("Content copied to clipboard successfully", style="bold green")
            )
        except Exception as e:
            console.print(Panel(f"Failed to copy to clipboard: {e}", style="red"))

    # Save to file if output is not console
    if output_mode.lower() != "console":
        try:
            output_file = Path(output_mode)
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
    # Handle initialization if requested
    if init:
        handle_init(force)
        raise typer.Exit()

    # Clear console and show banner
    clear_console()
    banner_text = (
        "[bold cyan]Interactive File Browser & Extractor[/bold cyan]\n"
        "Browse directories, preview content, and extract files for LLM contexts."
    )
    console.print(Panel(banner_text, style="bold green", expand=False))

    # Load and merge configuration
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

    # Scan directory and get selected files
    selected_files = scan_and_select_files(
        directory, recursive, filter, ignore, non_interactive
    )

    # Process and output the selected files
    process_output(selected_files, directory, output, config["copy_to_clipboard"])


if __name__ == "__main__":
    app()
