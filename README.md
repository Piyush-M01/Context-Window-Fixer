# Filesystem Explorer MCP Server

A professional Model Context Protocol (MCP) server that provides tools for exploring filesystems, reading various file types, and cloning GitHub repositories with comprehensive error handling.

## Features

- **File Reading**: Read text files, PDFs, and images with intelligent encoding detection
- **Directory Listing**: Browse and list files across multiple directories with configurable depth
- **GitHub Integration**: Clone repositories directly to your storage
- **Smart File Matching**: Case-insensitive partial file matching to handle filenames with tokens
- **Comprehensive Error Handling**: Professional error handling with detailed logging
- **Type Safety**: Full type hints throughout the codebase
- **Configurable**: Centralized configuration for easy customization

## Installation

### Prerequisites

- Python 3.12 or higher
- `uv` package manager (optional but recommended)
- Git (for cloning repositories)

### Setup

1. Clone or navigate to the project directory:
```bash
cd /home/piyush/mcp_project/context_window_fixer
```

2. Install dependencies:
```bash
uv sync
```

Or with pip:
```bash
pip install mcp mcpo pypdf
```

3. The server will automatically create required directories on first run.

## Usage

### Starting the Server

Run the MCP server using:

```bash
uv run main.py
```

Or with `mcpo` on a specific port:

```bash
uv run mcpo --port 8001 -- uv run main.py
```

### Available Tools

#### 1. `read_file(file_name: str) -> str`

Read the contents of a file with automatic type detection.

**Supported file types:**
- **Text files**: UTF-8 encoding with latin-1 fallback
- **PDF files**: Extracts text content from PDF documents
- **Images**: Returns base64-encoded image data (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.svg`)

**Features:**
- Case-insensitive partial file name matching
- Automatic file type detection
- Binary file detection
- Comprehensive error messages

**Example:**
```python
# Full filename
content = read_file("document.txt")

# Partial filename (useful when upload portals add tokens)
content = read_file("document")  # Matches "document_abc123.txt"
```

#### 2. `list_files(directory: str = ".") -> str`

List all files and subdirectories in a directory.

**Parameters:**
- `directory`: Path to list (use `"."` or `""` for default storage and upload paths)

**Features:**
- Recursive directory traversal with configurable depth (default: 100 levels)
- Skips `.git` directories automatically
- Sorted output for readability
- Permission error handling

**Example:**
```python
# List default directories
files = list_files(".")

# List specific directory
files = list_files("/path/to/directory")

# List home directory
files = list_files("~")
```

#### 3. `clone_github_repo(url: str) -> str`

Clone a GitHub repository to the storage directory.

**Parameters:**
- `url`: GitHub repository URL (supports `https://`, `http://`, and `git@` formats)

**Features:**
- Automatic repository name extraction
- Duplicate detection
- 5-minute timeout for large repositories
- Git availability check

**Example:**
```python
# Clone a repository
result = clone_github_repo("https://github.com/user/repo.git")

# Also accepts URLs without .git extension
result = clone_github_repo("https://github.com/user/repo")
```

## Configuration

All configuration is centralized in `config.py`. You can customize:

### Paths
```python
STORAGE_PATH = os.path.join(os.getcwd(), "storage")
UPLOADED_FILES_PATH = "/path/to/uploads/"
```

### File Type Extensions
```python
IMAGE_EXTENSIONS = frozenset(['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'])
PDF_EXTENSION = '.pdf'
```

### Traversal Limits
```python
DEFAULT_MAX_DEPTH = 100  # Maximum directory depth for listing
```

### Logging
```python
LOG_FILE = "mcp_server.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Error Handling

The server uses custom exceptions for specific error scenarios:

- `FileReadError`: File cannot be read
- `FileNotFoundError`: File not found in search paths
- `DirectoryAccessError`: Directory cannot be accessed
- `RepositoryCloneError`: Git repository cloning failed
- `InvalidFileTypeError`: Unsupported or invalid file type

All errors return user-friendly messages while logging detailed information for debugging.

## Project Structure

```
context_window_fixer/
├── main.py              # Main MCP server with tools
├── filereader.py        # File reading utilities
├── config.py            # Configuration settings
├── exceptions.py        # Custom exception classes
├── pyproject.toml       # Project dependencies
├── mcp_server.log       # Server logs
└── storage/             # Default storage directory
```

## Logging

The server logs to two locations:
1. **File**: `mcp_server.log` (persistent logs)
2. **stderr**: Console output (for real-time monitoring)

Log levels include:
- `INFO`: General operations (file reads, directory listings)
- `WARNING`: Non-critical issues (permission denied, missing paths)
- `ERROR`: Critical errors (file not found, read failures)
- `DEBUG`: Detailed debugging information

## Development

### Type Checking

The codebase uses type hints throughout. You can run type checking with:

```bash
mypy main.py filereader.py config.py exceptions.py
```

### Code Style

The code follows:
- PEP 8 style guide
- Comprehensive docstrings (Google style)
- Type hints on all functions
- Clear error messages

### Testing

Test files are included:
- `test_list_files.py`: Tests directory listing
- `test_clone.py`: Tests repository cloning

Run tests with:
```bash
python test_list_files.py
python test_clone.py
```

## Troubleshooting

### Common Issues

**Issue**: File not found even though it exists
- **Solution**: Check that the file is in one of the search paths (storage or uploads directory). Use `list_files()` to verify.

**Issue**: Permission denied errors
- **Solution**: Ensure the server has read permissions for the target directory. Check file/directory permissions.

**Issue**: PDF text extraction fails
- **Solution**: Ensure `pypdf` is installed. Some PDFs with only images won't extract text.

**Issue**: Git clone fails
- **Solution**: Verify Git is installed and the repository URL is correct. Check network connectivity.

**Issue**: Encoding errors
- **Solution**: The server attempts UTF-8 first, then falls back to latin-1. Binary files are automatically detected.

## License

This project is licensed under the terms specified in the project repository.

## Support

For issues, questions, or contributions, please refer to the project repository.

---

**Version**: 0.1.0  
**Python**: ≥3.12  
**Last Updated**: 2025-11-30
