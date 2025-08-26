"""
Test configuration and utilities.
"""

import tempfile
import shutil
from pathlib import Path
import pytest

from folder_indexer.config import Config, IndexingConfig, SearchConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files for testing."""
    # Create directory structure
    (temp_dir / "subdir").mkdir()
    (temp_dir / "subdir" / "nested").mkdir()
    
    # Create files
    files = {
        "test.txt": "This is a test file with some content.",
        "data.json": '{"name": "test", "value": 123}',
        "script.py": "def hello():\n    print('Hello, world!')",
        "README.md": "# Test Project\n\nThis is a test project.",
        "subdir/file.txt": "Nested file content.",
        "subdir/nested/deep.txt": "Deep nested content."
    }
    
    for file_path, content in files.items():
        full_path = temp_dir / file_path
        full_path.write_text(content)
    
    return temp_dir


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return Config(
        indexing=IndexingConfig(
            ignore_patterns=["*.pyc", "__pycache__/"],
            max_file_size=1,  # 1MB for testing
            include_hidden=False
        ),
        search=SearchConfig(
            max_results=50,
            highlight=True
        )
    )
