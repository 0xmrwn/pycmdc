import os
from pathlib import Path
from typing import List

import toml
import typer
from InquirerPy import inquirer
from rich.console import Console
from rich.panel import Panel

console = Console()


class ConfigManager:
    """
    Manages configuration loading, saving, and interactive initialization.
    """

    def __init__(self):
        self.config_dir = self.get_config_dir()
        self.config_path = self.config_dir / "config.toml"

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
            "recursive": False,
            "copy_to_clipboard": True,
            "print_to_console": False,
            "depth": 1,  # Default depth: only immediate subdirectories
            "tiktoken_model": "o200k_base",
        }

    def interactive_config(self) -> dict:
        """Run the interactive configuration setup process."""
        console.print(
            Panel(
                "[bold cyan]Welcome to CMDC Configuration![/bold cyan]\n"
                "Let's set up your preferences for the file browser.",
                style="bold green",
            )
        )

        copy_to_clipboard = inquirer.confirm(
            message="Do you want to automatically copy selected content to clipboard?",
            default=True,
        ).execute()

        recursive = inquirer.confirm(
            message="Do you want to browse directories recursively by default?",
            default=False,
        ).execute()

        # Ask for default depth (only used if recursive mode is not selected)
        default_depth_str = inquirer.text(
            message="Enter default scanning depth (e.g., 1 for immediate children):",
            default="1",
        ).execute()
        try:
            default_depth = int(default_depth_str)
            if default_depth < 1:
                default_depth = 1
        except ValueError:
            default_depth = 1

        default_patterns = self.get_default_ignore_patterns()
        use_default_ignores = inquirer.confirm(
            message="Would you like to use the recommended ignore patterns?",
            default=True,
        ).execute()

        if use_default_ignores:
            ignore_patterns = inquirer.checkbox(
                message="Select patterns to ignore:",
                instruction="Space to toggle, Enter to confirm",
                choices=default_patterns,
                default=default_patterns,
            ).execute()
        else:
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
                    message=(
                        "Enter file extension (e.g., .py) or press enter to finish:"
                    ),
                ).execute()
                if not ext:
                    break
                if not ext.startswith("."):
                    ext = f".{ext}"
                filters.append(ext)

        # Ask for token encoding model for tiktoken
        encoding_model = inquirer.text(
            message="Enter token encoding model to use (default: o200k_base):",
            default="o200k_base",
        ).execute()

        print_to_console = inquirer.confirm(
            message="Do you want to print the context dump to console by default?",
            default=False,
        ).execute()

        return {
            "copy_to_clipboard": copy_to_clipboard,
            "recursive": recursive,
            "ignore_patterns": ignore_patterns,
            "filters": filters,
            "depth": default_depth,
            "tiktoken_model": encoding_model,
            "print_to_console": print_to_console,
        }

    def get_file_config(self) -> dict:
        """Load configuration from file if it exists."""
        if not self.config_path.exists():
            console.print(
                Panel(
                    "[yellow]Welcome to CMDC![/yellow]\n"
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
        return env_config

    def load_config(self) -> dict:
        """
        Load configuration using a layered approach:
        1. Start with defaults
        2. Update with file config
        3. Update with environment variables
        """
        config = self.get_default_config()
        config.update(self.get_file_config())
        config.update(self.get_env_config())
        return config

    def handle_config(self, force: bool) -> None:
        """Handle the interactive configuration setup process."""
        if self.config_path.exists() and not force:
            overwrite = inquirer.confirm(
                message=(
                    "Configuration file already exists. Do you want to overwrite it?"
                ),
                default=False,
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
                    "[green]Configuration saved successfully to:[/green]\n"
                    f"{self.config_path}",
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
