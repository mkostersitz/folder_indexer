"""
File system watcher for real-time index updates.
"""

import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Set, Dict, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, DirCreatedEvent, DirDeletedEvent, DirModifiedEvent
from rich.console import Console

from .config import Config
from .indexer import DirectoryIndexer


class IndexUpdateHandler(FileSystemEventHandler):
    """Handles filesystem events and updates the index accordingly."""
    
    def __init__(self, indexer: DirectoryIndexer, config: Config):
        super().__init__()
        self.indexer = indexer
        self.config = config
        self.console = Console()
        self.pending_updates: Set[str] = set()
        self.last_update_time = time.time()
        
    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored."""
        return self.indexer._should_ignore(Path(path))
    
    def _queue_update(self, path: str):
        """Queue a path for index update."""
        if not self._should_ignore(path):
            self.pending_updates.add(path)
            self.last_update_time = time.time()
    
    def _process_pending_updates(self):
        """Process queued updates after a short delay to batch operations."""
        current_time = time.time()
        if current_time - self.last_update_time > 2.0 and self.pending_updates:  # 2 second delay
            paths_to_update = self.pending_updates.copy()
            self.pending_updates.clear()
            
            with self.indexer.ix.writer() as writer:
                for path in paths_to_update:
                    path_obj = Path(path)
                    try:
                        if path_obj.exists():
                            # File/directory exists, update or add it
                            self._update_single_path(writer, path_obj)
                        else:
                            # File/directory was deleted, remove from index
                            writer.delete_by_term('path', str(path_obj))
                            self.console.print(f"[yellow]Removed from index: {path}[/yellow]")
                    except Exception as e:
                        self.console.print(f"[red]Error updating {path}: {e}[/red]")
    
    def _update_single_path(self, writer, path: Path):
        """Update a single path in the index."""
        # First remove existing entry
        writer.delete_by_term('path', str(path))
        
        # Add new entry
        try:
            if path.is_file():
                stat_info = path.stat()
                content = self.indexer._extract_content(path)
                
                doc = {
                    'path': str(path),
                    'filename': path.name,
                    'dirname': str(path.parent),
                    'content': content,
                    'extension': path.suffix.lower(),
                    'size': stat_info.st_size,
                    'modified': datetime.fromtimestamp(stat_info.st_mtime),
                    'is_directory': "false",
                    'hash': self.indexer._get_file_hash(path)
                }
                writer.add_document(**doc)
                self.console.print(f"[green]Updated in index: {path}[/green]")
                
            elif path.is_dir():
                stat_info = path.stat()
                doc = {
                    'path': str(path),
                    'filename': path.name,
                    'dirname': str(path.parent),
                    'content': "",
                    'extension': "",
                    'size': 0,
                    'modified': datetime.fromtimestamp(stat_info.st_mtime),
                    'is_directory': "true",
                    'hash': ""
                }
                writer.add_document(**doc)
                self.console.print(f"[green]Updated directory in index: {path}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error updating {path}: {e}[/red]")
    
    def on_created(self, event):
        """Handle file/directory creation."""
        if not event.is_directory:
            self._queue_update(event.src_path)
        else:
            # For directories, we might want to index the entire new directory
            self._queue_update(event.src_path)
    
    def on_deleted(self, event):
        """Handle file/directory deletion."""
        self._queue_update(event.src_path)
    
    def on_modified(self, event):
        """Handle file/directory modification."""
        if not event.is_directory:  # Only update files, not directories
            self._queue_update(event.src_path)
    
    def on_moved(self, event):
        """Handle file/directory moves."""
        # Remove old path and add new path
        self._queue_update(event.src_path)  # Remove old
        self._queue_update(event.dest_path)  # Add new


class DirectoryWatcher:
    """Watches directories for changes and updates the search index."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.console = Console()
        self.indexer = DirectoryIndexer(config)
        self.observer = Observer()
        self.watched_paths: Dict[str, Any] = {}
        self.handler = IndexUpdateHandler(self.indexer, self.config)
    
    def add_watch(self, directory: Path, recursive: bool = True) -> bool:
        """Add a directory to watch for changes."""
        directory = directory.resolve()
        if not directory.exists() or not directory.is_dir():
            self.console.print(f"[red]Directory not found or not a directory: {directory}[/red]")
            return False
        
        directory_str = str(directory)
        if directory_str in self.watched_paths:
            self.console.print(f"[yellow]Directory already being watched: {directory}[/yellow]")
            return True
        
        try:
            watch = self.observer.schedule(self.handler, str(directory), recursive=recursive)
            self.watched_paths[directory_str] = watch
            self.console.print(f"[green]Now watching: {directory}[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]Failed to watch {directory}: {e}[/red]")
            return False
    
    def remove_watch(self, directory: Path) -> bool:
        """Remove a directory from being watched."""
        directory_str = str(directory.resolve())
        if directory_str not in self.watched_paths:
            self.console.print(f"[yellow]Directory not being watched: {directory}[/yellow]")
            return False
        
        try:
            watch = self.watched_paths[directory_str]
            self.observer.unschedule(watch)
            del self.watched_paths[directory_str]
            self.console.print(f"[yellow]Stopped watching: {directory}[/yellow]")
            return True
        except Exception as e:
            self.console.print(f"[red]Failed to stop watching {directory}: {e}[/red]")
            return False
    
    def start(self):
        """Start the file system watcher."""
        if not self.watched_paths:
            self.console.print("[yellow]No directories to watch. Add some directories first.[/yellow]")
            return
        
        self.observer.start()
        self.console.print("[green]File system watcher started.[/green]")
        
        try:
            while True:
                time.sleep(1)
                # Process any pending updates
                self.handler._process_pending_updates()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the file system watcher."""
        self.observer.stop()
        self.observer.join()
        self.console.print("[yellow]File system watcher stopped.[/yellow]")
    
    def get_watched_directories(self) -> list[str]:
        """Get list of currently watched directories."""
        return list(self.watched_paths.keys())
    
    def watch_indexed_directories(self):
        """Automatically watch all currently indexed directories."""
        indexed_dirs = self.indexer.get_indexed_directories()
        
        for dir_path in indexed_dirs:
            directory = Path(dir_path)
            if directory.exists() and directory.is_dir():
                self.add_watch(directory)
        
        if indexed_dirs:
            self.console.print(f"[green]Set up watching for {len(indexed_dirs)} indexed directories.[/green]")
        else:
            self.console.print("[yellow]No indexed directories found to watch.[/yellow]")
