# CLAUDE.md

Interactive CLI tool for browsing, selecting, and formatting code files for LLM context windows. Uses typer + rich + InquirerPy.

## Toolchain

| Concern     | Tool              |
|-------------|-------------------|
| Runtime     | Python >=3.9      |
| Deps        | uv                |
| Lint        | ruff              |
| Format      | ruff format       |
| Typecheck   | pyright (basic)   |
| Test        | pytest            |
| Pre-commit  | ruff + pre-commit-hooks + commitizen |

## Quality gates

```bash
make setup      # uv sync --dev + pre-commit install
make lint       # ruff check + ruff format --check
make typecheck  # pyright
make test       # pytest
make format     # auto-fix formatting
make fix        # auto-fix lint + format
make clean      # remove build artifacts
```

Every change must pass `make lint`, `make typecheck`, and `make test` before merge.

## Project layout

```
cmdc/                  # Main package (flat layout, not src/)
  cli.py               # Typer CLI entry point and command routing
  config_manager.py    # Layered config: defaults → file → gitignore → env → CLI
  file_browser.py      # Directory traversal, file filtering, interactive selection
  output_handler.py    # XML output formatting, clipboard, file writing
  utils.py             # Token counting (tiktoken), directory tree building
  prompt_style.py      # InquirerPy styling
tests/                 # pytest test suite (mirrors cmdc/ modules)
```

## Rules

- All tool config lives in `pyproject.toml`. No `.ini` or `.cfg` files.
- Conventional commits enforced via commitizen pre-commit hook.
- B008 is ignored in ruff — typer requires `typer.Option()` / `typer.Argument()` in function defaults.
- InquirerPy `reportPrivateImportUsage` suppressed in pyright — library stubs are broken.
