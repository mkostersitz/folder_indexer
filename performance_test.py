#!/usr/bin/env python3
"""
Simple demonstration of the performance difference between regular and filenames-only indexing.
"""

import time
import tempfile
from pathlib import Path
from src.folder_indexer.indexer import DirectoryIndexer
from src.folder_indexer.config import Config

def create_test_files(directory: Path, num_files: int = 100):
    """Create test files with content for performance testing."""
    directory.mkdir(exist_ok=True)
    
    for i in range(num_files):
        # Create files with substantial content
        file_path = directory / f"test_file_{i:03d}.txt"
        content = f"This is test file {i}\n" + "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50
        file_path.write_text(content, encoding='utf-8')
        
        # Create some Python files
        if i % 10 == 0:
            py_file = directory / f"script_{i:03d}.py"
            py_content = f'''#!/usr/bin/env python3
"""
Test Python file {i}
"""

def function_{i}():
    """Test function {i}"""
    return "Hello from function {i}"

if __name__ == "__main__":
    print(function_{i}())
'''
            py_file.write_text(py_content, encoding='utf-8')

def test_indexing_performance():
    """Test and compare indexing performance."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "performance_test"
        
        print("Creating test files...")
        create_test_files(test_dir, 200)  # Create 200 text files + 20 Python files
        print(f"Created test directory with files at: {test_dir}")
        
        config = Config()
        indexer = DirectoryIndexer(config)
        
        # Test regular indexing (with content)
        print("\n=== Testing Regular Indexing (with content) ===")
        start_time = time.time()
        count_full = indexer.index_directory(test_dir, show_progress=True, filenames_only=False)
        full_time = time.time() - start_time
        print(f"Regular indexing: {count_full} items in {full_time:.2f} seconds")
        
        # Clear the index for the next test
        indexer.remove_directory(test_dir, show_progress=False)
        
        # Test filenames-only indexing
        print("\n=== Testing Filenames-Only Indexing ===")
        start_time = time.time()
        count_fast = indexer.index_directory(test_dir, show_progress=True, filenames_only=True)
        fast_time = time.time() - start_time
        print(f"Filenames-only indexing: {count_fast} items in {fast_time:.2f} seconds")
        
        # Calculate improvement
        if full_time > 0:
            speedup = full_time / fast_time
            percent_faster = ((full_time - fast_time) / full_time) * 100
            print(f"\n🚀 Performance Improvement:")
            print(f"   Filenames-only is {speedup:.1f}x faster")
            print(f"   That's {percent_faster:.1f}% faster than regular indexing")
        
        print(f"\n📊 Summary:")
        print(f"   Regular indexing:     {full_time:.2f}s")
        print(f"   Filenames-only:       {fast_time:.2f}s")
        print(f"   Time saved:           {full_time - fast_time:.2f}s")

if __name__ == "__main__":
    test_indexing_performance()
