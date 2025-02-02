# pycmdc

[![PyPI version](https://badge.fury.io/py/pycmdc.svg)](https://badge.fury.io/py/pycmdc)
[![Python Version](https://img.shields.io/pypi/pyversions/pycmdc.svg)](https://pypi.org/project/pycmdc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Tired of Cmd+C'ing your way though files to feed your LLMs code context? Use cmdc instead to browse, grab, and format your code with style. Stop the manual copy-paste madness.

## Features

- 🌳 **Interactive Tree View**: Browse directories with a tree structure visualization
- 🔍 **Fuzzy Search**: Quickly find and select files in large directories
- 📋 **Clipboard Integration**: Automatically copy selected content to clipboard
- 🏷️ **Structured Output**: XML-like tag format optimized for LLM context
- 🔢 **Token Counter**: Built-in token counting using `tiktoken` for LLM context size awareness
- ⚙️ **Configurable**: Extensive configuration options for ignore patterns, file filters, and more
- 🎯 **Multiple Output Modes**: Output to clipboard, console, or file
- ⌨️ **Intuitive Navigation**: Keyboard shortcuts for quick file selection

## Installation

Install using pip:

```bash
pip install pycmdc
```

## Quick Start

1. Navigate to your project directory:
```bash
cd your-project
```

2. Run cmdc:
```bash
cmdc
```

This will open an interactive file browser where you can:
- Navigate using arrow keys (↑/↓)
- Toggle selection using arrow keys (←/→)
- Search files by typing
- Select all files using Ctrl+A
- Toggle all selections using Ctrl+D
- Confirm selection with Enter

## Usage

### Basic Commands

```bash
# Browse current directory
cmdc

# Browse specific directory
cmdc /path/to/directory

# Configure cmdc
cmdc --config

# Show help
cmdc --help
```

### Advanced Options

```bash
# Filter by file extensions
cmdc --filters .py .js .ts

# Ignore specific patterns
cmdc --ignore "node_modules" "*.pyc"

# Recursive directory traversal
cmdc --recursive

# Set maximum directory depth
cmdc --depth 2

# Save output to file
cmdc --output output.txt

# Non-interactive mode (select all matching files)
cmdc --non-interactive
```

### Configuration

Run the configuration wizard:
```bash
cmdc --config
```

Show current configuration:
```bash
cmdc --config-show
```

List ignore patterns:
```bash
cmdc --list-ignore
```

Add new ignore patterns:
```bash
cmdc --add-ignore "*.log" "temp/*"
```

## Output Format

The tool generates structured output in an XML-like format:

```xml
<summary>
<selected_files>
file1.py
file2.js
</selected_files>
<directory_structure>
your-project/
├── file1.py
├── file2.js
└── src/
    └── other.py
</directory_structure>
</summary>

<open_file>
file1.py
<contents>
# Content of file1.py
</contents>
</open_file>

<open_file>
file2.js
<contents>
// Content of file2.js
</contents>
</open_file>
```

## Configuration File

The configuration file is stored in:
- Linux/macOS: `~/.config/cmdc/config.toml`
- Windows: `%APPDATA%\cmdc\config.toml`

Example configuration:
```toml
[cmdc]
recursive = false
depth = 1
copy_to_clipboard = true
print_to_console = false
ignore_patterns = [".git", "node_modules", "__pycache__", "*.pyc"]
filters = [".py", ".js"]
tiktoken_model = "o200k_base"
```

## Environment Variables

You can override configuration using environment variables:
- `CMDC_FILTERS`: Comma-separated list of file extensions
- `CMDC_IGNORE`: Comma-separated list of ignore patterns
- `CMDC_RECURSIVE`: Set to "true" for recursive mode
- `CMDC_COPY_CLIPBOARD`: Set to "true" to enable clipboard copy

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
