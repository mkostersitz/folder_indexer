"""
Configuration management for folder indexer.
"""

import os
import tomllib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class IndexingConfig:
    """Configuration for indexing behavior."""
    ignore_patterns: List[str] = field(default_factory=lambda: [
        "*.pyc", "__pycache__/", ".git/", "node_modules/", "*.log",
        ".DS_Store", "Thumbs.db", "*.tmp", "*.swp"
    ])
    max_file_size: int = 10  # MB
    include_hidden: bool = False
    follow_symlinks: bool = False
    verbose_errors: bool = False  # Show detailed error messages for skipped files


@dataclass
class SearchConfig:
    """Configuration for search behavior."""
    max_results: int = 100
    highlight: bool = True
    fuzzy_threshold: float = 0.8


@dataclass
class Config:
    """Main configuration container."""
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)


def load_config() -> Config:
    """Load configuration from file or use defaults."""
    config_paths = [
        Path.home() / ".folder-indexer.toml",
        Path.cwd() / ".folder-indexer.toml",
        Path.cwd() / "folder-indexer.toml",
    ]
    
    config_data = {}
    
    # Find and load the first available config file
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    config_data = tomllib.load(f)
                break
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
    
    # Create config objects with loaded data
    indexing_data = config_data.get("indexing", {})
    search_data = config_data.get("search", {})
    
    indexing_config = IndexingConfig(
        ignore_patterns=indexing_data.get("ignore_patterns", IndexingConfig().ignore_patterns),
        max_file_size=indexing_data.get("max_file_size", IndexingConfig().max_file_size),
        include_hidden=indexing_data.get("include_hidden", IndexingConfig().include_hidden),
        follow_symlinks=indexing_data.get("follow_symlinks", IndexingConfig().follow_symlinks),
    )
    
    search_config = SearchConfig(
        max_results=search_data.get("max_results", SearchConfig().max_results),
        highlight=search_data.get("highlight", SearchConfig().highlight),
        fuzzy_threshold=search_data.get("fuzzy_threshold", SearchConfig().fuzzy_threshold),
    )
    
    return Config(indexing=indexing_config, search=search_config)


def get_index_dir() -> Path:
    """Get the directory where search indexes are stored."""
    if os.name == "nt":  # Windows
        base_dir = Path(os.environ.get("APPDATA", Path.home()))
    else:  # Unix-like
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    index_dir = base_dir / "folder-indexer" / "indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    return index_dir
