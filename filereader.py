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
from config import Config
import base64
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

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
            self.logger.debug(f"File '{file_name}' not found in provided file list")
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

    def read_pdf_file(self, file_path: str) -> str:
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
                self.logger.debug(f"Extracted text from page {page_num}")
            
            if not text.strip():
                self.logger.warning(f"No text extracted from PDF: {file_path}")
                return "Warning: PDF file appears to be empty or contains only images."
            
            self.logger.info(f"Successfully extracted text from PDF: {file_path}")
            return text
            
        except ImportError as e:
            self.logger.error("pypdf library not available")
            raise FileReadError(
                file_name=file_path,
                reason="pypdf library not installed"
            ) from e
        except Exception as e:
            self.logger.error(f"Error reading PDF file '{file_path}': {e}")
            raise FileReadError(
                file_name=file_path,
                reason=f"PDF extraction failed: {str(e)}"
            ) from e

    def read_image_file(self, file_path: str) -> str:
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
            self.logger.info(f"Successfully encoded image file: {file_path}")
            
            return f"Image file ({file_extension}) - Base64 encoded:\n{encoded_content}"
            
        except Exception as e:
            self.logger.error(f"Error reading image file '{file_path}': {e}")
            raise FileReadError(
                file_name=file_path,
                reason=f"Image read failed: {str(e)}"
            ) from e


    def read_text_file(self, file_path: str) -> str:
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
            self.logger.error(f"Error checking file type: {e}")
            raise FileReadError(file_name=file_path, reason=str(e)) from e
        
        # Try reading as text with encoding fallback
        for encoding in [Config.ENCODING_PRIMARY, Config.ENCODING_FALLBACK]:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    contents = f.read()
                    self.logger.info(f"Successfully read text file with {encoding} encoding")
                    return contents
            except UnicodeDecodeError:
                if encoding == Config.ENCODING_FALLBACK:
                    raise FileReadError(
                        file_name=file_path,
                        reason=f"Cannot decode file with {encoding} encoding"
                    )
                self.logger.debug(f"Failed to read with {encoding}, trying fallback")
                continue
            except Exception as e:
                self.logger.error(f"Error reading file: {e}")
                raise FileReadError(file_name=file_path, reason=str(e)) from e
        
        # This should never be reached but included for safety
        raise FileReadError(file_name=file_path, reason="All encoding attempts failed")
