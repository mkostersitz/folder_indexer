"""
Core indexing functionality for scanning and indexing directory structures.
"""

import os
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Iterator, Optional, Dict, Any, List
import pathspec
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, DATETIME, NUMERIC
from whoosh.filedb.filestore import FileStorage
from rich.progress import Progress, TaskID
from rich.console import Console

from .config import Config, get_index_dir


class DirectoryIndexer:
    """Handles indexing of directory structures."""
    
    # Define the search schema
    SCHEMA = Schema(
        path=ID(stored=True, unique=True),
        filename=TEXT(stored=True),
        dirname=TEXT(stored=True),
        content=TEXT(stored=True),
        extension=TEXT(stored=True),
        size=NUMERIC(stored=True),
        modified=DATETIME(stored=True),
        is_directory=ID(stored=True),
        hash=ID(stored=True)
    )
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.console = Console()
        self.index_dir = get_index_dir()
        self._setup_index()
        
    def _setup_index(self):
        """Initialize or open the search index."""
        if not index.exists_in(str(self.index_dir)):
            self.ix = index.create_in(str(self.index_dir), self.SCHEMA)
        else:
            self.ix = index.open_dir(str(self.index_dir))
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored based on patterns."""
        if not self.config.indexing.include_hidden and path.name.startswith('.'):
            return True
            
        spec = pathspec.PathSpec.from_lines('gitwildmatch', self.config.indexing.ignore_patterns)
        return spec.match_file(str(path))
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, IOError):
            return ""
    
    def _extract_content(self, file_path: Path) -> str:
        """Extract text content from file if possible."""
        if file_path.stat().st_size > self.config.indexing.max_file_size * 1024 * 1024:
            return ""
            
        try:
            # Try to read as text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except (OSError, IOError, UnicodeDecodeError):
            return ""
    
    def _scan_directory(self, directory: Path) -> Iterator[Dict[str, Any]]:
        """Scan directory and yield file information."""
        try:
            for root, dirs, files in os.walk(directory, followlinks=self.config.indexing.follow_symlinks):
                root_path = Path(root)
                
                # Filter directories to ignore
                dirs[:] = [d for d in dirs if not self._should_ignore(root_path / d)]
                
                # Process directories
                for dir_name in dirs:
                    dir_path = root_path / dir_name
                    if self._should_ignore(dir_path):
                        continue
                        
                    yield {
                        'path': str(dir_path),
                        'filename': dir_name,
                        'dirname': str(root_path),
                        'content': "",
                        'extension': "",
                        'size': 0,
                        'modified': datetime.fromtimestamp(dir_path.stat().st_mtime),
                        'is_directory': "true",
                        'hash': ""
                    }
                
                # Process files
                for file_name in files:
                    file_path = root_path / file_name
                    if self._should_ignore(file_path):
                        continue
                    
                    try:
                        stat_info = file_path.stat()
                        content = self._extract_content(file_path) if file_path.is_file() else ""
                        
                        yield {
                            'path': str(file_path),
                            'filename': file_name,
                            'dirname': str(root_path),
                            'content': content,
                            'extension': file_path.suffix.lower(),
                            'size': stat_info.st_size,
                            'modified': datetime.fromtimestamp(stat_info.st_mtime),
                            'is_directory': "false",
                            'hash': self._get_file_hash(file_path) if file_path.is_file() else ""
                        }
                    except (OSError, IOError) as e:
                        self.console.print(f"[red]Error processing {file_path}: {e}[/red]")
                        continue
                        
        except (OSError, IOError) as e:
            self.console.print(f"[red]Error scanning {directory}: {e}[/red]")
    
    def index_directory(self, directory: Path, show_progress: bool = True) -> int:
        """Index a directory structure."""
        directory = directory.resolve()
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        # First, remove any existing entries for this directory
        self.remove_directory(directory, show_progress=False)
        
        indexed_count = 0
        
        with Progress(console=self.console, disable=not show_progress) as progress:
            if show_progress:
                task = progress.add_task(f"Indexing {directory}", total=None)
            
            writer = self.ix.writer()
            try:
                for item in self._scan_directory(directory):
                    writer.add_document(**item)
                    indexed_count += 1
                    
                    if show_progress and indexed_count % 100 == 0:
                        progress.update(task, description=f"Indexed {indexed_count} items from {directory}")
                
                writer.commit()
                
            except Exception as e:
                writer.cancel()
                raise e
        
        if show_progress:
            self.console.print(f"[green]Successfully indexed {indexed_count} items from {directory}[/green]")
        
        return indexed_count
    
    def remove_directory(self, directory: Path, show_progress: bool = True) -> int:
        """Remove a directory from the index."""
        directory = directory.resolve()
        directory_str = str(directory)
        
        removed_count = 0
        
        with self.ix.searcher() as searcher:
            # Find all documents that are under this directory
            results = searcher.documents(dirname=directory_str)
            paths_to_remove = [result['path'] for result in results]
            
            # Also find the directory itself
            dir_results = searcher.documents(path=directory_str)
            paths_to_remove.extend([result['path'] for result in dir_results])
            
            # Find subdirectories by searching for paths that start with the directory path
            from whoosh.query import Prefix
            subdir_query = Prefix('path', directory_str + os.sep)
            subdir_results = searcher.search(subdir_query, limit=None)
            paths_to_remove.extend([result['path'] for result in subdir_results])
        
        if paths_to_remove:
            writer = self.ix.writer()
            try:
                for path in paths_to_remove:
                    writer.delete_by_term('path', path)
                    removed_count += 1
                
                writer.commit()
                
                if show_progress:
                    self.console.print(f"[yellow]Removed {removed_count} items for directory {directory}[/yellow]")
            except Exception as e:
                writer.cancel()
                raise e
        
        return removed_count
    
    def get_indexed_directories(self) -> List[str]:
        """Get list of all indexed directories."""
        directories = set()
        
        with self.ix.searcher() as searcher:
            # Search for all directory entries
            from whoosh.query import Term
            dir_query = Term('is_directory', 'true')
            results = searcher.search(dir_query, limit=None)
            
            for result in results:
                directories.add(result['path'])
            
            # Also get parent directories of files
            file_query = Term('is_directory', 'false')
            file_results = searcher.search(file_query, limit=None)
            
            for result in file_results:
                parent = str(Path(result['path']).parent)
                directories.add(parent)
        
        return sorted(list(directories))
    
    def rebuild_index(self) -> int:
        """Rebuild the entire search index."""
        directories = self.get_indexed_directories()
        
        # Clear the index
        writer = self.ix.writer()
        writer.commit(mergetype=index.CLEAR)
        
        total_indexed = 0
        
        for directory in directories:
            dir_path = Path(directory)
            if dir_path.exists():
                total_indexed += self.index_directory(dir_path)
            else:
                self.console.print(f"[yellow]Skipping non-existent directory: {directory}[/yellow]")
        
        self.console.print(f"[green]Rebuilt index with {total_indexed} total items[/green]")
        return total_indexed
