# cmdc/cli.py
import typer
from pathlib import Path
from typing import List, Optional
import sys

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
    config: bool = typer.Option(
        False,
        "--config",
        help="Run interactive configuration setup.",
    ),
    config_show: bool = typer.Option(
        False,
        "--config-show",
        help="Display current configuration settings.",
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
        help="Maximum depth for subdirectory exploration. "
        "Overrides config setting if provided and recursive mode is not used.",
    ),
    encoding_model: Optional[str] = typer.Option(
        "o200k_base",
        "--encoding-model",
        help="Token encoding model to use for token counting (overrides config).",
    ),
):
    """
    Interactive CLI tool for browsing and selecting files for LLM contexts.

    By default, running `cmdc` will browse the current directory. Use the options
    to modify the behavior. To run the configuration initialization, use the `--config`
    flag (with `--force` to override an existing configuration).
    """
    # Create a ConfigManager instance to load and (if needed) initialize configuration.
    config_manager = ConfigManager()

    if config:
        config_manager.handle_config(force)
        raise typer.Exit()

    if config_show:
        config_manager.display_config()
        raise typer.Exit()

    clear_console()
    banner_text = (
        "[bold cyan]Interactive File Browser & Extractor[/bold cyan]\n"
        "Browse directories, preview content, and extract files for LLM contexts."
    )
    console.print(Panel(banner_text, style="bold green", expand=False))

    # Load the layered configuration.
    config = config_manager.load_config()

    # Override tiktoken model if provided on the command line
    if encoding_model is not None:
        config["tiktoken_model"] = encoding_model

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
    file_browser = FileBrowser(
        directory,
        recursive,
        filters,
        ignore,
        depth,
        encoding_model=config.get("tiktoken_model", "o200k_base"),
    )
    selected_files, total_tokens = file_browser.scan_and_select_files(non_interactive)

    # Check if -o was explicitly provided by checking sys.argv
    output_explicitly_provided = any(arg in ["--output", "-o"] for arg in sys.argv[1:])

    should_print_to_console = (
        output_explicitly_provided and output.lower() == "console"
    ) or (not output_explicitly_provided and config.get("print_to_console", False))

    # Instantiate the OutputHandler to process and output file contents.
    output_handler = OutputHandler(
        directory=directory,
        copy_to_clipboard=config.get("copy_to_clipboard", True),
        print_to_console=should_print_to_console,
    )
    output_handler.process_output(selected_files, output)

    # If content was copied to clipboard (and we're in console mode),
    # display the total tokens (this information is not part of the copied content).
    if output.lower() == "console" and config.get("copy_to_clipboard", True):
        console.print(
            Panel(
                f"Total tokens copied to clipboard: {total_tokens}", style="bold green"
            )
        )


if __name__ == "__main__":
    app()
