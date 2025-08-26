"""
Tests for the indexer module.
"""

import pytest
from pathlib import Path

from folder_indexer.indexer import DirectoryIndexer
from folder_indexer.config import Config


def test_indexer_creation(test_config):
    """Test that indexer can be created."""
    indexer = DirectoryIndexer(test_config)
    assert indexer is not None
    assert indexer.config == test_config


def test_index_directory(sample_files, test_config):
    """Test indexing a directory."""
    indexer = DirectoryIndexer(test_config)
    count = indexer.index_directory(sample_files, show_progress=False)
    
    # Should index files + directories  
    # Root directory is not included in the count, only subdirectories
    # 6 files + 2 subdirectories = 8 items
    assert count == 8


def test_ignore_patterns(temp_dir, test_config):
    """Test that ignore patterns work."""
    # Create files that should be ignored
    (temp_dir / "test.pyc").write_text("compiled python")
    (temp_dir / "__pycache__").mkdir()
    (temp_dir / "__pycache__" / "module.pyc").write_text("cached")
    
    # Create files that should be indexed
    (temp_dir / "test.py").write_text("python source")
    
    indexer = DirectoryIndexer(test_config)
    count = indexer.index_directory(temp_dir, show_progress=False)
    
    # Should only index the .py file and the main directory
    assert count == 2


def test_remove_directory(sample_files, test_config):
    """Test removing a directory from index."""
    indexer = DirectoryIndexer(test_config)
    
    # First index the directory
    count = indexer.index_directory(sample_files, show_progress=False)
    assert count > 0
    
    # Then remove it
    removed_count = indexer.remove_directory(sample_files, show_progress=False)
    assert removed_count > 0


def test_get_indexed_directories(sample_files, test_config):
    """Test getting list of indexed directories."""
    indexer = DirectoryIndexer(test_config)
    
    # Initially should be empty
    dirs = indexer.get_indexed_directories()
    assert isinstance(dirs, list)
    
    # Index a directory
    indexer.index_directory(sample_files, show_progress=False)
    
    # Should now contain the indexed directory
    dirs = indexer.get_indexed_directories()
    assert len(dirs) > 0
    assert str(sample_files) in dirs or any(str(sample_files) in d for d in dirs)
