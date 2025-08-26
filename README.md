# Folder Indexer

A fast and efficient Python tool for indexing directory structures and enabling rapid search across files and folders.

## Features

- **Fast Indexing**: Efficiently indexes directory structures with support for large filesystems
- **Real-time Updates**: Automatically updates the index when files/folders change using filesystem watchers
- **Powerful Search**: Search by filename, path, content, or metadata with advanced filtering options
- **Flexible Configuration**: Customizable indexing rules with support for ignore patterns
- **CLI Interface**: Easy-to-use command-line interface with rich output formatting
- **Performance Optimized**: Built with Whoosh search engine for lightning-fast queries
- **Cross-Platform**: Works on Windows, macOS, and Linux

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows 10+, macOS 10.14+, or Linux (any modern distribution)
- **Memory**: Minimum 512MB RAM (more recommended for large directories)
- **Storage**: Varies based on indexed content (typically 1-5% of indexed data size)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Option 1: Install from Source (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/folder-indexer.git
   cd folder-indexer
   ```

2. **Create a virtual environment:**
   
   **On Windows:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
   
   **On macOS/Linux:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Upgrade pip (recommended):**
   ```bash
   python -m pip install --upgrade pip
   ```

4. **Install the package:**
   ```bash
   pip install -e .
   ```

5. **Verify installation:**
   ```bash
   folder-indexer --version
   ```

### Option 2: Development Installation

If you plan to contribute or modify the code:

1. **Follow steps 1-3 from Option 1**

2. **Install with development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks (optional):**
   ```bash
   pre-commit install
   ```

4. **Run tests to verify everything works:**
   ```bash
   pytest
   ```

### Virtual Environment Management

**Activating the environment:**
- Windows: `.venv\Scripts\activate`
- macOS/Linux: `source .venv/bin/activate`

**Deactivating the environment:**
```bash
deactivate
```

**Removing the virtual environment:**
Simply delete the `.venv` directory when you no longer need it.

### Troubleshooting Installation

**Common Issues:**

1. **Permission errors:** Use `--user` flag or ensure virtual environment is activated
2. **Python version conflicts:** Ensure you're using Python 3.8+
3. **Missing dependencies:** Try upgrading pip: `python -m pip install --upgrade pip`

**Verify installation:**
```bash
# Check if folder-indexer is installed
folder-indexer --help

# Check Python environment
python -c "import folder_indexer; print(folder_indexer.__version__)"
```

## Getting Started

Once installed, you can start using folder-indexer immediately:

### 1. Index Your First Directory

```bash
# Index your current directory
folder-indexer index .

# Index a specific directory
folder-indexer index /path/to/your/documents

# Index with progress display disabled
folder-indexer index /path/to/directory --no-progress
```

### 2. Search Your Files

```bash
# Simple filename search
folder-indexer search "README"

# Search with file patterns
folder-indexer search "*.py" --pattern "*.py"

# Search in file contents
folder-indexer search "function" --content

# Search with filters
folder-indexer search "config" --type file --max-size 100
```

### 3. Monitor Changes (Optional)

```bash
# Watch a directory for changes
folder-indexer watch /path/to/directory

# Watch without recursing into subdirectories
folder-indexer watch /path/to/directory --no-recursive
```

### 4. View Your Index

```bash
# List all indexed directories
folder-indexer list

# Show index statistics
folder-indexer stats

# Quick find commands
folder-indexer find --extension py
folder-indexer find --large-files 10
folder-indexer find --recent 7
```

## Quick Start

**TL;DR:** Want to jump right in? Here's the fastest way:

```bash
# 1. Clone and install
git clone https://github.com/yourusername/folder-indexer.git
cd folder-indexer
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# 2. Index and search
folder-indexer index .
folder-indexer search "*.py"
```

For detailed installation and usage instructions, see the sections below.

## Usage

### Basic Commands

- `index <path>` - Index a directory structure
- `search <query>` - Search indexed files and directories
- `watch <path>` - Start watching a directory for changes
- `list` - Show all indexed directories
- `remove <path>` - Remove a directory from the index
- `rebuild` - Rebuild the entire search index

### Search Options

- `--pattern` - Filter by file pattern (e.g., `*.py`, `*.txt`)
- `--content` - Search within file contents
- `--modified` - Filter by modification date
- `--size` - Filter by file size
- `--type` - Filter by file type (file/directory)

### Configuration

Create a `.folder-indexer.toml` file in your home directory or project root:

```toml
[indexing]
# Patterns to ignore (gitignore syntax)
ignore_patterns = [
    "*.pyc",
    "__pycache__/",
    ".git/",
    "node_modules/",
    "*.log"
]

# Maximum file size to index content (in MB)
max_file_size = 10

# Whether to index hidden files
include_hidden = false

[search]
# Maximum number of results to return
max_results = 100

# Whether to highlight search terms in results
highlight = true
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/folder-indexer.git
cd folder-indexer
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src tests
flake8 src tests
mypy src
```

## Architecture

The project is structured around several key components:

- **Indexer**: Core indexing engine that scans directories and builds the search index
- **Searcher**: Query engine for fast search operations
- **Watcher**: Filesystem monitoring for real-time updates
- **CLI**: Command-line interface built with Click
- **Storage**: Whoosh-based search index storage

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Whoosh](https://whoosh.readthedocs.io/) for search capabilities
- Uses [Watchdog](https://python-watchdog.readthedocs.io/) for filesystem monitoring
- CLI powered by [Click](https://click.palletsprojects.com/)
- Rich output formatting with [Rich](https://rich.readthedocs.io/)
