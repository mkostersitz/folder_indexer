"""
Folder Indexer - A tool for indexing and fast searching of folder structures.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .indexer import DirectoryIndexer
from .searcher import FileSearcher
from .watcher import DirectoryWatcher

__all__ = ["DirectoryIndexer", "FileSearcher", "DirectoryWatcher"]
