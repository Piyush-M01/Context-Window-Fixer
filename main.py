"""
Filesystem Explorer MCP Server.

This MCP server provides tools for exploring filesystems, reading files,
and cloning GitHub repositories with comprehensive error handling.
"""

from mcp.server.fastmcp import FastMCP
import os
import subprocess
import logging
import sys
from typing import Optional
from pathlib import Path
import base64

from filereader import FileReader
from config import Config
from pypdf import PdfReader

from exceptions import (
    FileReadError,
    FileNotFoundError as CustomFileNotFoundError,
    DirectoryAccessError,
    RepositoryCloneError,
    InvalidFileTypeError
)

# Configure logging to write to file and stderr
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler(sys.stderr)
    ]
)

# Initialize components
logger = logging.getLogger(__name__)
file_reader = FileReader("", logger)
mcp = FastMCP(Config.SERVER_NAME)

# Ensure required directories exist
Config.ensure_directories_exist()

# Track all files found during directory listing
list_of_files: set[str] = set()


def find_file_in_paths(file_name: str, search_paths: list[str]) -> Optional[str]:
    """
    Search for a file across multiple directory paths.
    
    Performs a case-insensitive partial match to handle files with
    tokens added by upload portals.
    
    Args:
        file_name: Name of the file to search for (can be partial)
        search_paths: List of directory paths to search
        
    Returns:
        Full path to the matched file, or None if not found
    """
    file_name_lower = file_name.lower()
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            logger.warning(f"Search path does not exist: {search_path}")
            continue
            
        try:
            for root, dirs, files in os.walk(search_path):
                # Skip .git directories
                dirs[:] = [d for d in dirs if d != '.git']
                
                # Check for partial match
                matched_file = next(
                    (f for f in files if file_name_lower in f.lower()),
                    None
                )
                
                if matched_file:
                    full_path = os.path.join(root, matched_file)
                    logger.info(f"File '{file_name}' found at: {full_path}")
                    return full_path
                    
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {search_path}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error searching in {search_path}: {e}")
            continue
    
    return None


def read_pdf_file(file_path: str) -> str:
    """
    Read and extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text from the PDF
        
    Raises:
        FileReadError: If PDF cannot be read or text cannot be extracted
    """
    try:        
        reader = PdfReader(file_path)
        text = ""
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text() or ""
            text += page_text
            logger.debug(f"Extracted text from page {page_num}")
        
        if not text.strip():
            logger.warning(f"No text extracted from PDF: {file_path}")
            return "Warning: PDF file appears to be empty or contains only images."
        
        logger.info(f"Successfully extracted text from PDF: {file_path}")
        return text
        
    except ImportError as e:
        logger.error("pypdf library not available")
        raise FileReadError(
            file_name=file_path,
            reason="pypdf library not installed"
        ) from e
    except Exception as e:
        logger.error(f"Error reading PDF file '{file_path}': {e}")
        raise FileReadError(
            file_name=file_path,
            reason=f"PDF extraction failed: {str(e)}"
        ) from e


def read_image_file(file_path: str) -> str:
    """
    Read an image file and return base64-encoded content.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Base64-encoded image data with format description
        
    Raises:
        FileReadError: If image cannot be read
    """
    try:        
        with open(file_path, 'rb') as f:
            binary_content = f.read()
            encoded_content = base64.b64encode(binary_content).decode('utf-8')
            
        file_extension = Path(file_path).suffix
        logger.info(f"Successfully encoded image file: {file_path}")
        
        return f"Image file ({file_extension}) - Base64 encoded:\n{encoded_content}"
        
    except Exception as e:
        logger.error(f"Error reading image file '{file_path}': {e}")
        raise FileReadError(
            file_name=file_path,
            reason=f"Image read failed: {str(e)}"
        ) from e


def read_text_file(file_path: str) -> str:
    """
    Read a text file with encoding fallback.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        Contents of the text file
        
    Raises:
        FileReadError: If file cannot be read
        InvalidFileTypeError: If file is binary
    """
    # Check if file is binary
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(Config.BINARY_CHECK_BYTES)
            if b'\x00' in sample:
                raise InvalidFileTypeError(
                    file_name=file_path,
                    file_type="binary",
                    reason="File contains null bytes and cannot be read as text"
                )
    except Exception as e:
        if isinstance(e, InvalidFileTypeError):
            raise
        logger.error(f"Error checking file type: {e}")
        raise FileReadError(file_name=file_path, reason=str(e)) from e
    
    # Try reading as text with encoding fallback
    for encoding in [Config.ENCODING_PRIMARY, Config.ENCODING_FALLBACK]:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                contents = f.read()
                logger.info(f"Successfully read text file with {encoding} encoding")
                return contents
        except UnicodeDecodeError:
            if encoding == Config.ENCODING_FALLBACK:
                raise FileReadError(
                    file_name=file_path,
                    reason=f"Cannot decode file with {encoding} encoding"
                )
            logger.debug(f"Failed to read with {encoding}, trying fallback")
            continue
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise FileReadError(file_name=file_path, reason=str(e)) from e
    
    # This should never be reached but included for safety
    raise FileReadError(file_name=file_path, reason="All encoding attempts failed")


@mcp.tool()
def read_file(file_name: str) -> str:
    """
    Read the contents of a file.
    
    Supports text files, PDFs, and images. Images are returned as base64-encoded data.
    The function performs a case-insensitive partial match on the filename.
    
    Args:
        file_name: The name of the file to read (can be partial)
        
    Returns:
        The contents of the file, or an error message
    """
    if not file_name or not file_name.strip():
        return "Error: File name cannot be empty."
    
    file_name = file_name.strip()
    logger.info(f"Reading file: {file_name}")
    logger.debug(f"Cached files: {len(list_of_files)} files")
    
    try:
        # First check in cached file list
        try:
            matched_file = file_reader.check_file_exists(file_name, list_of_files)
            logger.debug(f"File found in cache: {matched_file}")
        except CustomFileNotFoundError:
            logger.debug(f"File not in cache, searching directories")
        
        # Search in configured paths
        search_paths = Config.get_search_paths()
        file_path = find_file_in_paths(file_name, search_paths)
        
        if file_path is None:
            searched = ", ".join(search_paths)
            logger.error(f"File '{file_name}' not found in any search path")
            return f"Error: File '{file_name}' not found.\nSearched in: {searched}"
        
        # Determine file type and read accordingly
        if Config.is_pdf_file(file_path):
            return read_pdf_file(file_path)
        elif Config.is_image_file(file_path):
            return read_image_file(file_path)
        else:
            return read_text_file(file_path)
            
    except InvalidFileTypeError as e:
        return f"Error: {e.message}\n{e.details}"
    except FileReadError as e:
        return f"Error: {e.message}\n{e.details}"
    except CustomFileNotFoundError as e:
        return f"Error: {e.message}"
    except PermissionError:
        logger.error(f"Permission denied for file '{file_name}'")
        return f"Error: Permission denied for file '{file_name}'."
    except Exception as e:
        logger.exception(f"Unexpected error reading file '{file_name}'")
        return f"Error: An unexpected error occurred: {str(e)}"


@mcp.tool()
def clone_github_repo(url: str) -> str:
    """
    Clone a GitHub repository.
    
    Args:
        url: The URL of the GitHub repository to clone
        
    Returns:
        Success message with cloned repository path, or error message
    """
    if not url or not url.strip():
        return "Error: Repository URL cannot be empty."
    
    url = url.strip()
    logger.info(f"Cloning repository: {url}")
    
    try:
        # Validate URL format
        if not url.startswith(('http://', 'https://', 'git@')):
            return "Error: Invalid repository URL format. Must start with http://, https://, or git@"
        
        # Extract repository name from URL
        repo_name = url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        if not repo_name:
            return "Error: Could not extract repository name from URL."
        
        repo_destination = os.path.join(Config.STORAGE_PATH, repo_name)
        
        # Check if repository already exists
        if os.path.exists(repo_destination):
            logger.warning(f"Repository already exists at: {repo_destination}")
            return f"Warning: Repository '{repo_name}' already exists at '{repo_destination}'."
        
        # Construct and execute git clone command
        command = ["git", "clone", url, repo_destination]
        
        logger.debug(f"Executing: {' '.join(command)}")
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        logger.info(f"Repository cloned successfully to: {repo_destination}")
        return f"Repository '{url}' cloned successfully to '{repo_destination}'."
        
    except subprocess.TimeoutExpired:
        logger.error(f"Clone operation timed out for: {url}")
        return f"Error: Clone operation timed out after 5 minutes."
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone failed: {e.stderr}")
        error_msg = e.stderr.strip() if e.stderr else "Unknown git error"
        return f"Error cloning repository: {error_msg}"
    except FileNotFoundError:
        logger.error("Git command not found")
        return "Error: Git is not installed or not in PATH."
    except Exception as e:
        logger.exception(f"Unexpected error cloning repository '{url}'")
        return f"Error: An unexpected error occurred: {str(e)}"


def build_files(directory: str, max_depth: int = Config.DEFAULT_MAX_DEPTH) -> str:
    """
    Build a string representation of files and directories.
    
    Args:
        directory: The root directory to list
        max_depth: Maximum depth to traverse (0 = current dir only, 1 = one level deep, etc.)
        
    Returns:
        Formatted string listing of directory contents
        
    Raises:
        DirectoryAccessError: If directory cannot be accessed
    """
    if not os.path.exists(directory):
        raise DirectoryAccessError(
            directory=directory,
            reason="Directory does not exist"
        )
    
    if not os.path.isdir(directory):
        raise DirectoryAccessError(
            directory=directory,
            reason="Path is not a directory"
        )
    
    output = ""
    
    def _list_dir(path: str, current_depth: int = 0) -> None:
        """Recursive helper to list directory contents."""
        nonlocal output
        
        try:
            items = os.listdir(path)
            
            # Separate directories and files
            dirs = [
                item for item in items 
                if os.path.isdir(os.path.join(path, item)) and item != '.git'
            ]
            files = [
                item for item in items 
                if os.path.isfile(os.path.join(path, item))
            ]
            
            # Update global file cache
            list_of_files.update(files)
            
            # Build output
            output += f"Directory: {path}\n"
            if dirs:
                output += f"  Subdirectories: {', '.join(sorted(dirs))}\n"
            if files:
                output += f"  Files: {', '.join(sorted(files))}\n"
            output += "\n"
            
            # Recursively list subdirectories if within depth limit
            if current_depth < max_depth:
                for d in sorted(dirs):
                    _list_dir(os.path.join(path, d), current_depth + 1)
                    
        except PermissionError:
            output += f"Directory: {path}\n  Error: Permission denied\n\n"
            logger.warning(f"Permission denied: {path}")
        except Exception as e:
            output += f"Directory: {path}\n  Error: {str(e)}\n\n"
            logger.error(f"Error listing directory {path}: {e}")
    
    _list_dir(directory)
    return output


@mcp.tool()
def list_files(directory: str = ".") -> str:
    """
    List the files in a directory.
    
    Args:
        directory: The directory to list files from. 
                  Use "." or "" for default storage and upload paths.
                  
    Returns:
        Formatted list of files and directories
    """
    try:
        # Default to storage folder when directory is empty or "."
        if directory in (".", ""):
            output = "=== Storage Folder ===\n"
            try:
                output += build_files(Config.STORAGE_PATH, max_depth=Config.DEFAULT_MAX_DEPTH)
            except DirectoryAccessError as e:
                output += f"Error: {e.message}\n"
                logger.warning(f"Storage directory not accessible: {e.details}")
            
            # Also list uploaded files if path exists
            if os.path.exists(Config.UPLOADED_FILES_PATH):
                output += "\n=== Uploaded Files ===\n"
                try:
                    output += build_files(
                        Config.UPLOADED_FILES_PATH,
                        max_depth=Config.DEFAULT_MAX_DEPTH
                    )
                except DirectoryAccessError as e:
                    output += f"Error: {e.message}\n"
                    logger.warning(f"Upload directory not accessible: {e.details}")
        else:
            # List specific directory
            directory = directory.strip()
            
            # Expand user home directory if needed
            directory = os.path.expanduser(directory)
            
            # Make absolute path if relative
            if not os.path.isabs(directory):
                directory = os.path.abspath(directory)
            
            output = build_files(directory, max_depth=Config.DEFAULT_MAX_DEPTH)
        
        logger.info("Listed files successfully")
        return output
        
    except DirectoryAccessError as e:
        logger.error(f"Directory access error: {e.message}")
        return f"Error: {e.message}\n{e.details}"
    except PermissionError as e:
        logger.error(f"Permission denied for directory '{directory}'")
        return f"Error: Permission denied for directory '{directory}'."
    except Exception as e:
        logger.exception(f"Unexpected error listing files in '{directory}'")
        return f"Error: An unexpected error occurred: {str(e)}"


if __name__ == "__main__":
    logger.info(f"Starting {Config.SERVER_NAME} MCP server")
    logger.info(f"Storage path: {Config.STORAGE_PATH}")
    logger.info(f"Upload path: {Config.UPLOADED_FILES_PATH}")
    mcp.run()