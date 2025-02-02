# cmdc/cli.py
import typer
from pathlib import Path
from typing import List, Optional

from cmdc.config_manager import ConfigManager
from cmdc.file_browser import FileBrowser
from cmdc.output_handler import OutputHandler
from cmdc.utils import clear_console

from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    help="Interactive CLI tool for browsing and selecting files for LLM contexts."
)
console = Console()


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
    filters: Optional[List[str]] = typer.Option(
        None,
        "--filters",
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
    depth: Optional[int] = typer.Option(
        None,
        "--depth",
        "-d",
        help="Maximum depth for subdirectory exploration. Overrides config setting if provided and recursive mode is not used.",
    ),
):
    """
    Interactive CLI tool for browsing and selecting files for LLM contexts.

    By default, running `cmdc` will browse the current directory. Use the options
    to modify the behavior. To run the configuration initialization, use the `--init`
    flag (with `--force` to override an existing configuration).
    """
    # Create a ConfigManager instance to load and (if needed) initialize configuration.
    config_manager = ConfigManager()

    if init:
        config_manager.handle_init(force)
        raise typer.Exit()

    clear_console()
    banner_text = (
        "[bold cyan]Interactive File Browser & Extractor[/bold cyan]\n"
        "Browse directories, preview content, and extract files for LLM contexts."
    )
    console.print(Panel(banner_text, style="bold green", expand=False))

    # Load the layered configuration.
    config = config_manager.load_config()

    # Use command-line arguments to override or complement configuration defaults.
    if directory is None:
        directory = Path.cwd()
    if filters is None:
        filters = config.get("filters", [])
    if ignore is None:
        ignore = config.get("ignore_patterns", [])
    else:
        ignore = config.get("ignore_patterns", []) + list(ignore)

    # Handle recursive and depth flags with proper priority:
    # 1. If --recursive is explicitly set (True/False), it takes highest priority
    # 2. If --depth is explicitly set, it overrides recursive mode
    # 3. Otherwise, fall back to config values
    if recursive is not None:
        # Explicit --recursive flag takes priority
        depth = None if recursive else config.get("depth", 1)
    elif depth is not None:
        # Explicit --depth flag overrides recursive mode
        recursive = False
    else:
        # Fall back to config values
        recursive = config.get("recursive", False)
        depth = None if recursive else config.get("depth", 1)

    # Instantiate the FileBrowser to scan and select files.
    file_browser = FileBrowser(directory, recursive, filters, ignore, depth)
    selected_files = file_browser.scan_and_select_files(non_interactive)

    # Instantiate the OutputHandler to process and output file contents.
    output_handler = OutputHandler(directory, config.get("copy_to_clipboard", True))
    output_handler.process_output(selected_files, output)


if __name__ == "__main__":
    app()
