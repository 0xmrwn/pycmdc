import os


def clear_console() -> None:
    """Clear the console screen in a cross-platform way."""
    if os.name == "nt":
        os.system("cls")
    else:
        print("\033[H\033[J", end="")
