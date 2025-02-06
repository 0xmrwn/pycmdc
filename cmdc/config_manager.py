import os
from pathlib import Path
from typing import List, Optional

import toml
import typer
from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cmdc.prompt_style import get_custom_style, get_style

console = Console()


class ConfigManager:
    """
    Manages configuration loading, saving, and interactive initialization.
    """

    def __init__(self):
        self.config_dir = self.get_config_dir()
        self.config_path = self.config_dir / "config.toml"
        self.current_directory = None

    @staticmethod
    def get_config_dir() -> Path:
        """
        Get the appropriate configuration directory following platform conventions.
        """
        if os.name == "nt":  # Windows
            app_data = os.getenv("APPDATA")
            if app_data:
                return Path(app_data) / "cmdc"
            return Path.home() / "AppData" / "Roaming" / "cmdc"
        else:  # Unix-like systems: follow XDG Base Directory Specification
            xdg_config = os.getenv("XDG_CONFIG_HOME")
            if xdg_config:
                return Path(xdg_config) / "cmdc"
            return Path.home() / ".config" / "cmdc"

    def ensure_config_dir(self) -> None:
        """Create the configuration directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_default_ignore_patterns() -> List[str]:
        """Return the default list of ignore patterns."""
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
            ".ruff_cache",
        ]

    @staticmethod
    def get_default_config() -> dict:
        """Return the default configuration."""
        return {
            "filters": [],
            "ignore_patterns": ConfigManager.get_default_ignore_patterns(),
            "use_gitignore": True,  # Whether to automatically parse .gitignore files
            "recursive": False,
            "copy_to_clipboard": True,
            "print_to_console": False,
            "depth": 1,  # Default depth: only immediate subdirectories
            "tiktoken_model": "o200k_base",
        }

    def interactive_config(self) -> dict:
        """Run the interactive configuration setup process."""
        style = get_custom_style()

        console.print(
            Panel(
                "[bold cyan]Configuration Setup[/bold cyan]\n"
                "Set defaults for file browsing and output.",
                style="bold green",
            )
        )

        # Core browsing behavior
        recursive = inquirer.confirm(
            message="Do you want to browse directories recursively by default?",
            default=False,
            style=style,
            amark="✓",
        ).execute()

        default_depth_str = inquirer.text(
            message="Enter default scanning depth (e.g., 1 for immediate children):",
            default="1",
            style=style,
            amark="✓",
        ).execute()
        try:
            default_depth = int(default_depth_str)
            if default_depth < 1:
                default_depth = 1
        except ValueError:
            default_depth = 1

        # Output preferences
        copy_to_clipboard = inquirer.confirm(
            message="Do you want to automatically copy selected content to clipboard?",
            default=True,
            style=style,
            amark="✓",
        ).execute()

        print_to_console = inquirer.confirm(
            message="Do you want to print the context dump to console by default?",
            default=False,
            style=style,
            amark="✓",
        ).execute()

        # Gitignore integration
        use_gitignore = inquirer.confirm(
            message="Do you want to automatically use .gitignore files in scanned directories?",
            default=True,
            style=style,
            amark="✓",
        ).execute()

        # File filtering
        default_patterns = self.get_default_ignore_patterns()
        use_default_ignores = inquirer.confirm(
            message="Would you like to use the recommended ignore patterns?",
            default=True,
            style=style,
            amark="✓",
        ).execute()

        if use_default_ignores:
            ignore_patterns = inquirer.checkbox(
                message="Select patterns to ignore:",
                instruction="Space to toggle, Enter to confirm, ctrl+a to select all",
                choices=default_patterns,
                default=default_patterns,
                style=style,
                amark="✓",
            ).execute()
        else:
            ignore_patterns = []

        # Allow adding custom patterns
        while inquirer.confirm(
            message="Would you like to add custom ignore patterns?",
            default=False,
            style=style,
            amark="✓",
        ).execute():
            pattern = inquirer.text(
                message="Enter pattern (e.g., *.log, temp/*, etc.):",
                style=style,
            ).execute()
            if pattern:
                ignore_patterns.append(pattern)

        # File extension filters
        use_filters = inquirer.confirm(
            message="Would you like to set default file extension filters?",
            default=False,
            style=style,
            amark="✓",
        ).execute()

        filters = []
        if use_filters:
            while True:
                ext = inquirer.text(
                    message=(
                        "Enter file extension (e.g., .py) or press enter to finish:"
                    ),
                    style=style,
                ).execute()
                if not ext:
                    break
                if not ext.startswith("."):
                    ext = f".{ext}"
                filters.append(ext)

        # Advanced settings
        encoding_model = inquirer.text(
            message="Enter token encoding model to use (default: o200k_base):",
            default="o200k_base",
            style=style,
            amark="✓",
        ).execute()

        return {
            "recursive": recursive,
            "depth": default_depth,
            "copy_to_clipboard": copy_to_clipboard,
            "print_to_console": print_to_console,
            "use_gitignore": use_gitignore,
            "ignore_patterns": ignore_patterns,
            "filters": filters,
            "tiktoken_model": encoding_model,
        }

    def get_file_config(self) -> dict:
        """Load configuration from file if it exists."""
        if not self.config_path.exists():
            console.print(
                Panel(
                    "[yellow]Welcome to cmdc![/yellow]\n"
                    "You're running with default settings. "
                    "To customize the behavior, run:\n"
                    "[bold cyan]cmdc --config[/bold cyan]",
                    title="Notice",
                    border_style="yellow",
                )
            )
            return {}
        try:
            file_config = toml.load(self.config_path)
            return file_config.get("cmdc", {})
        except Exception as e:
            console.print(
                Panel(
                    f"[yellow]Warning:[/yellow] Error reading config file: {e}",
                    style="yellow",
                )
            )
            return {}

    @staticmethod
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
        if os.getenv("CMDC_USE_GITIGNORE"):
            env_config["use_gitignore"] = (
                os.getenv("CMDC_USE_GITIGNORE").lower() == "true"
            )
        return env_config

    @staticmethod
    def get_gitignore_patterns(directory: Path) -> List[str]:
        """
        Parse .gitignore file in the given directory and return valid ignore patterns.
        Skips comments and empty lines.

        Handles directory-specific patterns by:
        1. Removing trailing slashes from directory patterns
        2. Converting directory patterns to match both the dir and its contents
        """
        gitignore_path = directory / ".gitignore"
        patterns = []

        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Remove trailing slash if present
                            if line.endswith("/"):
                                line = line.rstrip("/")
                            patterns.append(line)
                            # For directory patterns, also add pattern with /* to match contents
                            if not any(c in line for c in ["*", "?", "["]):
                                patterns.append(f"{line}/*")
            except Exception as e:
                console.print(
                    Panel(
                        f"[yellow]Warning:[/yellow] Error reading .gitignore file: {e}",
                        style="yellow",
                    )
                )

        return patterns

    def load_config(self, directory: Optional[Path] = None) -> dict:
        """
        Load configuration using a layered approach:
        1. Start with defaults
        2. Update with file config
        3. Update with gitignore patterns (if enabled and directory provided)
        4. Update with environment variables
        """
        config = self.get_default_config()
        config.update(self.get_file_config())

        # Add gitignore patterns if enabled and directory is provided
        if directory is not None and config.get("use_gitignore", True):
            gitignore_patterns = self.get_gitignore_patterns(directory)
            if gitignore_patterns:
                # Combine existing and gitignore patterns, removing duplicates
                existing_patterns = set(config.get("ignore_patterns", []))
                combined_patterns = sorted(
                    list(existing_patterns | set(gitignore_patterns))
                )
                config["ignore_patterns"] = combined_patterns

        config.update(self.get_env_config())
        return config

    def handle_config(self, force: bool) -> None:
        """Handle the interactive configuration setup process."""
        if self.config_path.exists() and not force:
            # Get the base style and override specific styles for this prompt
            base_style = {
                "question": "#FF7520 bold",  # Change to desired color
                "answered_question": "#AC4F15 bold",  # Change to desired color
            }
            custom_style = get_style(base_style, style_override=False)

            overwrite = inquirer.confirm(
                message=(
                    "Configuration file already exists. Do you want to overwrite it?"
                ),
                default=False,
                style=custom_style,
                amark="✓",
            ).execute()
            if not overwrite:
                console.print("[yellow]Configuration unchanged.[/yellow]")
                raise typer.Exit()
        self.ensure_config_dir()
        config_data = self.interactive_config()
        try:
            with open(self.config_path, "w") as f:
                toml.dump({"cmdc": config_data}, f)
            console.print(
                Panel(
                    "[bold green]Configuration saved successfully to:[/bold green]\n"
                    f"{self.config_path}",
                    title="Success",
                    border_style="green",
                )
            )
        except Exception as e:
            console.print(
                Panel(
                    f"[red]Error saving configuration:[/red]\n{str(e)}", title="Error"
                )
            )
            raise typer.Exit(1)

    def display_config(self) -> None:
        """Display the current configuration in a nicely formatted way."""
        # Check if config exists and load appropriate config
        has_config = self.config_path.exists()
        if has_config:
            current_config = self.get_file_config()
            title = "[bold green]Current Configuration[/bold green]"
            description = f"Configuration loaded from: {self.config_path}"
        else:
            current_config = self.get_default_config()
            title = "[bold yellow]Default Configuration[/bold yellow]"
            description = (
                "[yellow]No configuration file found. "
                "These are the default settings being used.[/yellow]\n"
                "To create a custom configuration, run: [bold cyan]cmdc --config[/bold cyan]"
            )

        # Create and configure the table
        table = Table(title=title, show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green", no_wrap=False)

        # Add rows for each configuration item
        for key, value in current_config.items():
            if isinstance(value, list):
                # Format lists in a compact way
                if not value:
                    formatted_value = "[italic]empty[/italic]"
                else:
                    # For ignore patterns and filters, show as comma-separated list
                    formatted_value = ", ".join(str(item) for item in value)
                    # If the list is too long, truncate it
                    if len(formatted_value) > 60:
                        items_shown = value[:3]
                        formatted_value = f"{', '.join(str(item) for item in items_shown)} [dim](+{len(value) - 3} more)[/dim]"
            elif isinstance(value, bool):
                # Format booleans with color
                formatted_value = (
                    "[green]enabled[/green]" if value else "[red]disabled[/red]"
                )
            else:
                formatted_value = str(value)

            # Convert key from snake_case to Title Case for display
            display_key = key.replace("_", " ").title()
            table.add_row(display_key, formatted_value)

        # Display the configuration
        console.print("\n" + description + "\n")
        console.print(table)
        console.print()  # Add a newline for better spacing

    def display_ignore_patterns(self) -> None:
        """Display the current ignore patterns from config or defaults."""
        config = self.load_config()
        ignore_patterns = config.get("ignore_patterns", [])

        table = Table(
            title="[bold cyan]Current Ignore Patterns[/bold cyan]",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Pattern", style="green")
        table.add_column("Source", style="cyan")

        # Display patterns from config first, then defaults if not in config
        default_patterns = set(self.get_default_ignore_patterns())
        config_patterns = set(ignore_patterns)

        for pattern in sorted(config_patterns):
            source = "Custom" if pattern not in default_patterns else "Default"
            table.add_row(pattern, source)

        # Show remaining default patterns that aren't in config
        for pattern in sorted(default_patterns - config_patterns):
            table.add_row(pattern, "Default (inactive)")

        console.print("\n")
        console.print(table)
        console.print(
            "\nTo add new patterns, use: [bold cyan]cmdc --add-ignore pattern1 pattern2[/bold cyan]"
        )
        console.print()

    def add_ignore_patterns(self, new_patterns: List[str]) -> None:
        """Add new patterns to the ignore list in the configuration."""
        self.ensure_config_dir()

        # Load existing config or create new one
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    config = toml.load(f)
            except Exception as e:
                console.print(f"[red]Error reading config file: {e}[/red]")
                raise typer.Exit(1)
        else:
            config = {"cmdc": self.get_default_config()}

        # Get current patterns from config or defaults
        current_patterns = set(
            config.get("cmdc", {}).get(
                "ignore_patterns", self.get_default_ignore_patterns()
            )
        )

        # Add new patterns
        added_patterns = []
        already_exists = []
        for pattern in new_patterns:
            if pattern in current_patterns:
                already_exists.append(pattern)
            else:
                current_patterns.add(pattern)
                added_patterns.append(pattern)

        # Update config
        if "cmdc" not in config:
            config["cmdc"] = {}
        config["cmdc"]["ignore_patterns"] = sorted(list(current_patterns))

        # Save updated config
        try:
            with open(self.config_path, "w") as f:
                toml.dump(config, f)

            if added_patterns:
                console.print(
                    Panel(
                        f"[green]Added {len(added_patterns)} new pattern(s):[/green]\n"
                        + "\n".join(f"• {pattern}" for pattern in added_patterns),
                        title="Success",
                    )
                )
            if already_exists:
                console.print(
                    Panel(
                        "[yellow]Already in ignore list:[/yellow]\n"
                        + "\n".join(f"• {pattern}" for pattern in already_exists),
                        title="Note",
                    )
                )
        except Exception as e:
            console.print(f"[red]Error saving config file: {e}[/red]")
            raise typer.Exit(1)
