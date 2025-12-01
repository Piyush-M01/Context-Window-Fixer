"""
Configuration settings for the filesystem-explorer MCP server.

This module centralizes all configuration values including paths,
file type definitions, and operational limits.
"""

import os
from pathlib import Path


class Config:
    """Configuration class for the filesystem-explorer MCP server."""
    
    # Server configuration
    SERVER_NAME = "filesystem-explorer"
    
    # Path configuration
    STORAGE_PATH = os.path.join(os.getcwd(), "storage")
    UPLOADED_FILES_PATH = "/home/piyush/.local/lib/python3.12/site-packages/open_webui/data/uploads/"
    
    # Logging configuration
    LOG_FILE = "mcp_server.log"
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    
    # File type definitions
    IMAGE_EXTENSIONS = frozenset(['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'])
    PDF_EXTENSION = '.pdf'
    BINARY_CHECK_BYTES = 1024  # Number of bytes to read for binary detection
    
    # Directory traversal limits
    DEFAULT_MAX_DEPTH = 100
    
    # File matching
    CASE_INSENSITIVE_MATCH = True
    
    # Encoding fallback chain
    ENCODING_PRIMARY = 'utf-8'
    ENCODING_FALLBACK = 'latin-1'
    
    @classmethod
    def ensure_directories_exist(cls) -> None:
        """
        Ensure that all required directories exist.
        Creates them if they don't exist.
        """
        Path(cls.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_search_paths(cls) -> list[str]:
        """
        Get all paths that should be searched for files.
        
        Returns:
            List of directory paths to search
        """
        paths = [cls.STORAGE_PATH]
        if os.path.exists(cls.UPLOADED_FILES_PATH):
            paths.append(cls.UPLOADED_FILES_PATH)
        return paths
    
    @classmethod
    def is_image_file(cls, filename: str) -> bool:
        """
        Check if a file is an image based on its extension.
        
        Args:
            filename: Name or path of the file
            
        Returns:
            True if the file is an image, False otherwise
        """
        return any(filename.lower().endswith(ext) for ext in cls.IMAGE_EXTENSIONS)
    
    @classmethod
    def is_pdf_file(cls, filename: str) -> bool:
        """
        Check if a file is a PDF based on its extension.
        
        Args:
            filename: Name or path of the file
            
        Returns:
            True if the file is a PDF, False otherwise
        """
        return filename.lower().endswith(cls.PDF_EXTENSION)
