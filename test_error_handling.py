#!/usr/bin/env python3
"""
Demonstrate the improved error handling for problematic files.
"""

import tempfile
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from folder_indexer.indexer import DirectoryIndexer
from folder_indexer.config import Config

def test_error_handling():
    """Test that our error handling works correctly."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create normal files
        (temp_path / "normal_file.txt").write_text("This is a normal file")
        
        # Create a file with a very long name (close to path limit)
        long_name = "a" * 200 + ".txt"  # 200 character filename
        long_file = temp_path / long_name
        try:
            long_file.write_text("This file has a very long name")
        except OSError:
            print("⚠️  Could not create file with very long name (OS limitation)")
        
        # Test with verbose errors disabled (default)
        print("\n=== Testing with verbose errors DISABLED (default) ===")
        config = Config()
        config.indexing.verbose_errors = False
        indexer = DirectoryIndexer(config)
        
        count = indexer.index_directory(temp_path, show_progress=True, filenames_only=True)
        print(f"Indexed {count} items")
        
        # Test with verbose errors enabled
        print("\n=== Testing with verbose errors ENABLED ===")
        config.indexing.verbose_errors = True
        indexer2 = DirectoryIndexer(config)
        
        count2 = indexer2.index_directory(temp_path, show_progress=True, filenames_only=True)
        print(f"Indexed {count2} items")
        
        print("\n✅ Error handling test completed!")

if __name__ == "__main__":
    test_error_handling()
