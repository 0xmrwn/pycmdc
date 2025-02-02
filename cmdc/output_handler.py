from pathlib import Path
from typing import List

import pyperclip
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


class OutputHandler:
    """
    Handles processing and outputting the content of selected files.
    The output can be directed to the console (with optional clipboard copy)
    or saved to a specified file.
    """

    def __init__(self, directory: Path, copy_to_clipboard: bool):
        self.directory = directory
        self.copy_to_clipboard = copy_to_clipboard

    def process_output(self, selected_files: List[str], output_mode: str) -> None:
        """
        Process and output the selected files' contents.
        """
        output_text = ""
        if output_mode.lower() == "console":
            console.print(
                Panel("[bold green]Extracted File Contents[/bold green]", expand=False)
            )

        for file_path_str in selected_files:
            file_path = self.directory / file_path_str
            try:
                content = file_path.read_text(encoding="utf-8")
                syntax = Syntax(
                    content,
                    file_path.suffix.lstrip("."),
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                )
                # Append file content in a marked-up format
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

        if output_mode.lower() == "console" and self.copy_to_clipboard:
            try:
                pyperclip.copy(output_text)
                console.print(
                    Panel(
                        "Content copied to clipboard successfully", style="bold green"
                    )
                )
            except Exception as e:
                console.print(Panel(f"Failed to copy to clipboard: {e}", style="red"))

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
