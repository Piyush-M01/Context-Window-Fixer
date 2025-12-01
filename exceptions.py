"""
Custom exceptions for the filesystem-explorer MCP server.

This module defines custom exception classes that provide more specific
error handling and better error messages for the MCP server.
"""


class FileSystemExplorerError(Exception):
    """Base exception for all filesystem-explorer errors."""
    
    def __init__(self, message: str, details: str = ""):
        """
        Initialize the base exception.
        
        Args:
            message: The main error message
            details: Additional details about the error
        """
        self.message = message
        self.details = details
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format the exception message with details if available."""
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class FileReadError(FileSystemExplorerError):
    """Exception raised when a file cannot be read."""
    
    def __init__(self, file_name: str, reason: str = ""):
        """
        Initialize the file read error.
        
        Args:
            file_name: Name of the file that couldn't be read
            reason: Specific reason for the failure
        """
        message = f"Failed to read file '{file_name}'"
        super().__init__(message, reason)
        self.file_name = file_name


class FileNotFoundError(FileSystemExplorerError):
    """Exception raised when a file cannot be found."""
    
    def __init__(self, file_name: str, searched_paths: list[str] = None):
        """
        Initialize the file not found error.
        
        Args:
            file_name: Name of the file that wasn't found
            searched_paths: List of paths that were searched
        """
        message = f"File '{file_name}' not found"
        details = ""
        if searched_paths:
            details = f"Searched in: {', '.join(searched_paths)}"
        super().__init__(message, details)
        self.file_name = file_name
        self.searched_paths = searched_paths or []


class DirectoryAccessError(FileSystemExplorerError):
    """Exception raised when a directory cannot be accessed."""
    
    def __init__(self, directory: str, reason: str = ""):
        """
        Initialize the directory access error.
        
        Args:
            directory: Path to the directory
            reason: Specific reason for the failure
        """
        message = f"Cannot access directory '{directory}'"
        super().__init__(message, reason)
        self.directory = directory


class RepositoryCloneError(FileSystemExplorerError):
    """Exception raised when a git repository cannot be cloned."""
    
    def __init__(self, url: str, reason: str = ""):
        """
        Initialize the repository clone error.
        
        Args:
            url: URL of the repository
            reason: Specific reason for the failure
        """
        message = f"Failed to clone repository '{url}'"
        super().__init__(message, reason)
        self.url = url


class InvalidFileTypeError(FileSystemExplorerError):
    """Exception raised when a file type is not supported or invalid."""
    
    def __init__(self, file_name: str, file_type: str = "", reason: str = ""):
        """
        Initialize the invalid file type error.
        
        Args:
            file_name: Name of the file
            file_type: Detected or expected file type
            reason: Specific reason for the failure
        """
        message = f"Invalid or unsupported file type for '{file_name}'"
        details = reason
        if file_type:
            details = f"Type: {file_type}" + (f", {reason}" if reason else "")
        super().__init__(message, details)
        self.file_name = file_name
        self.file_type = file_type
