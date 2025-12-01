"""
File synchronization module for the filesystem-explorer MCP server.

This module handles synchronization of files from the Open-WebUI uploads directory
to the local storage directory, ensuring that the server always works with
local copies of files.
"""

import os
import shutil
import logging
from config import Config

import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class SyncEventHandler(FileSystemEventHandler):
    """Event handler for watchdog file system events."""
    
    def __init__(self, synchronizer):
        self.synchronizer = synchronizer
        
    def on_created(self, event):
        if not event.is_directory:
            self.synchronizer.sync_single_file(event.src_path)
            
    def on_modified(self, event):
        if not event.is_directory:
            self.synchronizer.sync_single_file(event.src_path)
            
    def on_moved(self, event):
        if not event.is_directory:
            self.synchronizer.sync_single_file(event.dest_path)

class FileSynchronizer:
    """
    Handles synchronization of files from Open-WebUI uploads to local storage.
    """
    
    def __init__(self):
        self.source_dir = Config.UPLOADED_FILES_PATH
        self.dest_dir = Config.STORAGE_PATH
        self.observer = None
        
    def start_watching(self):
        """Start the background monitoring thread using watchdog."""
        if self.observer is not None and self.observer.is_alive():
            logger.warning("Synchronizer observer already running")
            return
            
        if not os.path.exists(self.source_dir):
            logger.warning(f"Source directory for sync does not exist: {self.source_dir}")
            return

        # Perform initial full sync
        logger.info("Performing initial full sync...")
        self.sync_all_files()
            
        event_handler = SyncEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.source_dir, recursive=True)
        self.observer.start()
        logger.info(f"Started watchdog file synchronizer on {self.source_dir}")
        
    def stop_watching(self):
        """Stop the background monitoring thread."""
        if self.observer is None:
            return
            
        self.observer.stop()
        self.observer.join()
        self.observer = None
        logger.info("Stopped watchdog file synchronizer")

    def sync_single_file(self, source_path: str):
        """Sync a single file from source to destination."""
        try:
            # Calculate relative path
            rel_path = os.path.relpath(source_path, self.source_dir)
            dest_path = os.path.join(self.dest_dir, rel_path)
            
            # Ensure dest directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy file with metadata
            shutil.copy2(source_path, dest_path)
            logger.info(f"Synced: {source_path} -> {dest_path}")
            
        except Exception as e:
            logger.error(f"Failed to sync file {source_path}: {e}")

    def sync_all_files(self) -> int:
        """
        Synchronize all files from source to destination (full scan).
        """
        if not os.path.exists(self.source_dir):
            return 0
            
        synced_count = 0
        
        try:
            # Walk through source directory
            for root, dirs, files in os.walk(self.source_dir):
                # Calculate relative path from source root
                rel_path = os.path.relpath(root, self.source_dir)
                
                # Create corresponding directory in destination
                dest_root = os.path.join(self.dest_dir, rel_path)
                if not os.path.exists(dest_root):
                    os.makedirs(dest_root)
                
                for file_name in files:
                    source_file = os.path.join(root, file_name)
                    self.sync_single_file(source_file)
                    synced_count += 1
                            
            if synced_count > 0:
                logger.info(f"Full synchronization complete. Synced {synced_count} files.")
            
            return synced_count
            
        except Exception as e:
            logger.error(f"Error during full file synchronization: {e}")
            return 0
