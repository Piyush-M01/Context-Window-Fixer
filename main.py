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
from synchronizer import FileSynchronizer
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
synchronizer = FileSynchronizer()
mcp = FastMCP(Config.SERVER_NAME)

# Ensure required directories exist
Config.ensure_directories_exist()

# Perform initial synchronization and start background monitoring
logger.info("Starting background file synchronizer...")
synchronizer.start_watching()

# Track all files found during directory listing
list_of_files: set[str] = set()


def update_list_of_files(file_path: str):
    logger.info(f"Updating list of files with: {file_path}")
    list_files(file_path)    

def normalize_name(name: str) -> str:
    """Normalize a name for fuzzy matching by lowercasing and replacing underscores with hyphens."""
    return name.lower().replace('_', '-')

def find_file_in_paths(file_name: str, search_paths: list[str]) -> Optional[str]:
    """
    Search for a file across multiple directory paths.
    
    Performs a case-insensitive partial match to handle files with
    tokens added by upload portals. Supports both simple filenames
    and paths with subdirectories (e.g., 'folder/file.txt').
    
    Args:
        file_name: Name or path of the file to search for (can be partial)
        search_paths: List of directory paths to search
        
    Returns:
        Full path to the matched file, or None if not found
    """
    normalized_search = normalize_name(file_name)
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            logger.warning(f"Search path does not exist: {search_path}")
            continue
            
        try:
            for root, dirs, files in os.walk(search_path):
                # Skip .git directories
                dirs[:] = [d for d in dirs if d != '.git']
                
                # Check for partial match against both filename and relative path
                for f in files:
                    full_path = os.path.join(root, f)
                    # Get the relative path from the search_path root
                    relative_path = os.path.relpath(full_path, search_path)
                    
                    # Normalize for comparison
                    norm_f = normalize_name(f)
                    norm_rel = normalize_name(relative_path)
                    
                    # Match against either the filename or the relative path
                    if (normalized_search in norm_f or 
                        normalized_search in norm_rel):
                        logger.info(f"File '{file_name}' matched to: {full_path} (relative: {relative_path})")
                        return full_path
                    
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {search_path}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error searching in {search_path}: {e}")
            continue
    
    return None


def find_directory_in_paths(directory_name: str, search_paths: list[str]) -> Optional[str]:
    """
    Search for a directory across multiple directory paths.
    
    Performs a case-insensitive partial match to find subdirectories.
    
    Args:
        directory_name: Name or path of the directory to search for
        search_paths: List of directory paths to search within
        
    Returns:
        Full path to the matched directory, or None if not found
    """
    normalized_search = normalize_name(directory_name)
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            logger.warning(f"Search path does not exist: {search_path}")
            continue
            
        try:
            for root, dirs, files in os.walk(search_path):
                # Skip .git directories
                dirs[:] = [d for d in dirs if d != '.git']
                
                # Check for partial match against directory names and relative paths
                for d in dirs:
                    full_path = os.path.join(root, d)
                    # Get the relative path from the search_path root
                    relative_path = os.path.relpath(full_path, search_path)
                    
                    # Normalize for comparison
                    norm_d = normalize_name(d)
                    norm_rel = normalize_name(relative_path)
                    
                    # Match against either the directory name or the relative path
                    if (normalized_search in norm_d or 
                        normalized_search in norm_rel):
                        logger.info(f"Directory '{directory_name}' matched to: {full_path} (relative: {relative_path})")
                        return full_path
                    
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {search_path}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error searching in {search_path}: {e}")
            continue
    
    return None



@mcp.tool()
def read_file(file_name: str) -> str:
    """
    Read the contents of a specific file.
    
    Supports text files, PDFs, and images. Images are returned as base64-encoded data.
    The function performs a case-insensitive partial match on the filename and supports
    reading files in subdirectories.
    
    Args:
        file_name: The name or path of the file to read. Can be:
                  - Just a filename: 'boom.txt'
                  - A relative path: 'small-test-repo/boom.txt'
                  - Partial matches are supported
         
    Returns:
        The contents of the file, or an error message
        
    Examples:
        - To read a file in a subdirectory: file_name = "small-test-repo/boom.txt"
        - To read a file by name only: file_name = "boom.txt"
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
            return file_reader.read_pdf_file(file_path)
        elif Config.is_image_file(file_path):
            return file_reader.read_image_file(file_path)
        else:
            return file_reader.read_text_file(file_path)
            
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

# @mcp.tool()
# def read_files_within_folder(folder_name: str) -> str:
#     """
#     Read all files within a folder.
    
#     Args:
#         folder_name: The name of the folder to read files from
        
#     Returns:
#         Success message with contents from each of the files, or error message
#     """
#     if not folder_name or not folder_name.strip():
#         return "Error: Folder name cannot be empty."
    
#     folder_name = folder_name.strip()
#     logger.info(f"Reading files within folder: {folder_name}")
    
#     try:
#         # Search in configured paths
#         search_paths = Config.get_search_paths()
#         folder_path = find_file_in_paths(folder_name, search_paths)
        
#         if folder_path is None:
#             searched = ", ".join(search_paths)
#             logger.error(f"Folder '{folder_name}' not found in any search path")
#             return f"Error: Folder '{folder_name}' not found.\nSearched in: {searched}"
        
#         # Read all files in the folder
#         files = os.listdir(folder_path)
#         file_contents = []
#         for file_name in files:
#             file_path = os.path.join(folder_path, file_name)
#             if os.path.isfile(file_path):
#                 try:
#                     file_content = read_file(file_name)
#                     file_contents.append(f"File: {file_name}\n{file_content}")
#                 except Exception as e:
#                     logger.error(f"Error reading file '{file_name}': {e}")
#                     file_contents.append(f"Error reading file '{file_name}': {e}")
        
#         if not file_contents:
#             return f"Error: No files found in folder '{folder_name}'."
        
#         return "\n".join(file_contents)
#     except Exception as e:
#         logger.exception(f"Unexpected error reading files within folder '{folder_name}'")
#         return f"Error: An unexpected error occurred: {str(e)}"
    
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
        
        update_list_of_files(repo_destination)
                
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




def get_most_recent_directory(path: str) -> Optional[str]:
    """Find the most recently modified directory in the given path."""
    try:
        if not os.path.exists(path):
            return None
            
        directories = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path) and item not in ['.git', '.github']:
                directories.append((item, os.path.getmtime(item_path)))
        
        if not directories:
            return None
            
        # Sort by mtime descending
        directories.sort(key=lambda x: x[1], reverse=True)
        return directories[0][0]
    except Exception:
        return None

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
    most_recent_dir = get_most_recent_directory(directory)
    
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
                dir_list = []
                for d in sorted(dirs):
                    # Mark the most recent directory if we are in the root storage path
                    if current_depth == 0 and d == most_recent_dir:
                        dir_list.append(f"{d} [MOST RECENT]")
                    else:
                        dir_list.append(d)
                output += f"  Subdirectories: {', '.join(dir_list)}\n"
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
    List the files and subdirectories in a directory.
    
    Args:
        directory: The directory to list files from. Can be:
                  - "." or "" (empty): Lists all files in default storage and upload directories
                  - A directory name: "small-test-repo" (searches in storage paths)
                  - An absolute path: "/home/user/folder"
                  
    Returns:
        Formatted list of files and directories with subdirectories and file counts
        
    Examples:
        - List all storage: directory = "." or directory = ""
        - List specific folder: directory = "small-test-repo"
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
            
            # First, try to find it in the search paths
            search_paths = Config.get_search_paths()
            found_directory = find_directory_in_paths(directory, search_paths)
            
            if found_directory:
                # Use the found directory
                directory = found_directory
                logger.info(f"Found directory in search paths: {directory}")
            else:
                # Expand user home directory if needed
                directory = os.path.expanduser(directory)
                
                # Make absolute path if relative
                if not os.path.isabs(directory):
                    directory = os.path.abspath(directory)
            
            # For specific directories, we want to see the contents, so use default depth
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


@mcp.tool()
def read_latest_content() -> str:
    """
    Find and read the most recently added/modified content (file or repository).
    
    This tool identifies the most recently modified item in the storage directory,
    whether it is a full repository (folder) or a single uploaded file.
    
    Use this tool to "read the last uploaded file", "check the latest repo",
    or "get the most recent context".
    
    Returns:
        The content of the most recent file or all files in the most recent repository.
    """
    try:
        storage_path = Config.STORAGE_PATH
        if not os.path.exists(storage_path):
            return f"Error: Storage directory does not exist: {storage_path}"
            
        # Find most recent item (file or dir)
        items = []
        for item in os.listdir(storage_path):
            if item in ['.git', '.github', '.DS_Store']:
                continue
                
            item_path = os.path.join(storage_path, item)
            mtime = os.path.getmtime(item_path)
            is_dir = os.path.isdir(item_path)
            items.append((item, item_path, mtime, is_dir))
            
        if not items:
            return "No files or repositories found in storage."
            
        # Sort by modification time (newest first)
        items.sort(key=lambda x: x[2], reverse=True)
        name, path, mtime, is_dir = items[0]
        
        from datetime import datetime
        timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        output = f"*** CONTEXT UPDATE: LATEST CONTENT DETECTED ***\n"
        output += f"Time: {current_time}\n"
        output += f"Latest Item: {name} ({'Directory/Repository' if is_dir else 'File'})\n"
        output += f"Last Modified: {timestamp}\n"
        output += f"Location: {path}\n"
        output += f"NOTE: Focus ONLY on the content below. Ignore previous context.\n\n"
        output += f"=== START OF CONTENT ===\n\n"
        
        files_content = []
        
        if is_dir:
            # It's a repository/directory - read all files inside
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d != '.git']
                
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                    relative_path = os.path.relpath(full_path, path)
                    
                    try:
                        if Config.is_image_file(file_name):
                            content = "[Image File]"
                        elif Config.is_pdf_file(file_name):
                            file_reader.file_path = full_path
                            content = file_reader.read_pdf_file(full_path)
                        else:
                            file_reader.file_path = full_path
                            try:
                                content = file_reader.read_text_file(full_path)
                            except InvalidFileTypeError:
                                content = "[Binary File]"
                        
                        files_content.append(f"--- File: {relative_path} ---\n{content}\n")
                    except Exception as e:
                        files_content.append(f"--- File: {relative_path} ---\nError: {str(e)}\n")
        else:
            # It's a single file - read it directly
            try:
                if Config.is_image_file(name):
                    content = "[Image File]"
                elif Config.is_pdf_file(name):
                    file_reader.file_path = path
                    content = file_reader.read_pdf_file(path)
                else:
                    file_reader.file_path = path
                    try:
                        content = file_reader.read_text_file(path)
                    except InvalidFileTypeError:
                        content = "[Binary File]"
                
                files_content.append(f"--- File: {name} ---\n{content}\n")
            except Exception as e:
                files_content.append(f"--- File: {name} ---\nError: {str(e)}\n")
                
        if not files_content:
            output += "No readable content found."
        else:
            output += "\n".join(files_content)
            
        output += "\n=== END OF CONTENT ===\n"
        
        logger.info(f"Chain: Read latest content '{name}' ({'dir' if is_dir else 'file'})")
        return output

    except Exception as e:
        logger.exception("Error in read_latest_content")
        return f"Error processing latest content: {str(e)}"



@mcp.tool()
def list_files_within_folder(folder_name: str) -> str:
    """
    List the files and subdirectories within a specific folder/directory.
    
    This tool is for listing DIRECTORY contents only. To read the contents 
    of an individual file, use the read_file() tool instead.
    
    Args:
        folder_name: The name of the FOLDER/DIRECTORY to list files from.
                    This must be a directory, not a file path.
        
    Returns:
        Formatted list of files and subdirectories in the folder
        
    Example:
        folder_name = "small-test-repo" will list all files in that directory
    """
    try:
        folder_name = folder_name.strip()
        
        # Search for the folder in configured search paths
        search_paths = Config.get_search_paths()
        folder_path = find_directory_in_paths(folder_name, search_paths)
        
        if folder_path is None:
            searched = ", ".join(search_paths)
            raise DirectoryAccessError(
                directory=folder_name,
                reason=f"Folder not found in search paths: {searched}"
            )
        
        if not os.path.isdir(folder_path):
            raise DirectoryAccessError(
                directory=folder_path,
                reason="Path is not a directory"
            )
        
        logger.info(f"Listing files in folder: {folder_path}")
        return build_files(folder_path, max_depth=Config.DEFAULT_MAX_DEPTH)
    except DirectoryAccessError as e:
        logger.error(f"Directory access error: {e.message}")
        return f"Error: {e.message}\n{e.details}"
    except PermissionError as e:
        logger.error(f"Permission denied for directory '{folder_path}'")
        return f"Error: Permission denied for directory '{folder_path}'."
    except Exception as e:
        logger.exception(f"Unexpected error listing files in '{folder_path}'")
        return f"Error: An unexpected error occurred: {str(e)}"        
        

if __name__ == "__main__":
    logger.info(f"Starting {Config.SERVER_NAME} MCP server")
    logger.info(f"Storage path: {Config.STORAGE_PATH}")
    logger.info(f"Upload path: {Config.UPLOADED_FILES_PATH}")
    mcp.run()