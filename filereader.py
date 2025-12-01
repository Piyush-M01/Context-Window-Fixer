"""
File reading utilities for the filesystem-explorer MCP server.

This module provides utilities for file operations including file existence
checking and content reading with proper error handling.
"""

import os
import logging
from typing import Optional
from pathlib import Path
from exceptions import FileNotFoundError as CustomFileNotFoundError, FileReadError


class FileReader:
    """
    Handles file reading operations with error handling and logging.
    
    This class provides methods for checking file existence (with partial matching)
    and reading file contents with proper error handling and logging.
    """
    
    def __init__(self, file_path: str, logger: logging.Logger):
        """
        Initialize the FileReader.
        
        Args:
            file_path: Default path to the file (can be empty)
            logger: Logger instance for logging operations
        """
        self.logger = logger
        self.file_path = file_path
    
    def check_file_exists(self, file_name: str, files: list[str] | set[str]) -> str:
        """
        Check if a file exists in the provided list/set of files.
        
        Performs a case-insensitive partial match, which is useful when
        upload portals add tokens to filenames.
        
        Args:
            file_name: The name of the file to search for (can be partial)
            files: List or set of file names to search through
            
        Returns:
            The matched filename from the files list
            
        Raises:
            CustomFileNotFoundError: If no matching file is found
        """
        # Convert to lowercase for case-insensitive matching
        file_name_lower = file_name.lower()
        
        # Find the first file that contains the search term
        matched_file = next(
            (f for f in files if file_name_lower in f.lower()), 
            None
        )
        
        if matched_file is None:
            self.logger.error(f"File '{file_name}' not found in provided file list")
            raise CustomFileNotFoundError(
                file_name=file_name,
                searched_paths=["provided file list"]
            )
        
        self.logger.debug(f"File '{file_name}' matched to '{matched_file}'")
        return matched_file
    
    def read_file(self, encoding: str = 'utf-8') -> str:
        """
        Read the contents of the file specified in self.file_path.
        
        Args:
            encoding: The encoding to use for reading the file (default: utf-8)
            
        Returns:
            The contents of the file as a string
            
        Raises:
            FileReadError: If the file cannot be read
            ValueError: If file_path is not set
        """
        if not self.file_path:
            raise ValueError("File path is not set")
        
        try:
            with open(self.file_path, 'r', encoding=encoding) as file:
                contents = file.read()
                self.logger.debug(f"Successfully read file: {self.file_path}")
                return contents
        except FileNotFoundError as e:
            self.logger.error(f"File not found: {self.file_path}")
            raise FileReadError(
                file_name=self.file_path,
                reason="File does not exist"
            ) from e
        except PermissionError as e:
            self.logger.error(f"Permission denied: {self.file_path}")
            raise FileReadError(
                file_name=self.file_path,
                reason="Permission denied"
            ) from e
        except UnicodeDecodeError as e:
            self.logger.error(f"Encoding error reading {self.file_path}: {e}")
            raise FileReadError(
                file_name=self.file_path,
                reason=f"Cannot decode file with {encoding} encoding"
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error reading {self.file_path}: {e}")
            raise FileReadError(
                file_name=self.file_path,
                reason=str(e)
            ) from e
    
    def read_file_lines(self, encoding: str = 'utf-8') -> list[str]:
        """
        Read the contents of the file as a list of lines.
        
        Args:
            encoding: The encoding to use for reading the file (default: utf-8)
            
        Returns:
            List of lines from the file
            
        Raises:
            FileReadError: If the file cannot be read
            ValueError: If file_path is not set
        """
        if not self.file_path:
            raise ValueError("File path is not set")
        
        try:
            with open(self.file_path, 'r', encoding=encoding) as file:
                lines = file.readlines()
                self.logger.debug(f"Successfully read {len(lines)} lines from: {self.file_path}")
                return lines
        except FileNotFoundError as e:
            self.logger.error(f"File not found: {self.file_path}")
            raise FileReadError(
                file_name=self.file_path,
                reason="File does not exist"
            ) from e
        except PermissionError as e:
            self.logger.error(f"Permission denied: {self.file_path}")
            raise FileReadError(
                file_name=self.file_path,
                reason="Permission denied"
            ) from e
        except UnicodeDecodeError as e:
            self.logger.error(f"Encoding error reading {self.file_path}: {e}")
            raise FileReadError(
                file_name=self.file_path,
                reason=f"Cannot decode file with {encoding} encoding"
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error reading {self.file_path}: {e}")
            raise FileReadError(
                file_name=self.file_path,
                reason=str(e)
            ) from e