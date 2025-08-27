#!/usr/bin/env python3
"""
Simple test to verify 64-bit file size support works correctly.
"""

import tempfile
from pathlib import Path
from datetime import datetime
from src.folder_indexer.indexer import DirectoryIndexer
from src.folder_indexer.config import Config

def test_large_file_size():
    """Test that we can handle file sizes larger than 32-bit integers."""
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a test indexer
        config = Config()
        indexer = DirectoryIndexer(config)
        
        # Test with a large file size (larger than 32-bit signed int max: 2,147,483,647)
        large_file_size = 4507566080  # ~4.2 GB (the size that caused the original error)
        
        print(f"Testing with file size: {large_file_size:,} bytes ({large_file_size / (1024**3):.1f} GB)")
        
        # Create a mock file entry with large size
        try:
            with indexer.ix.writer() as writer:
                writer.add_document(
                    path=str(temp_path / "large_file.dat"),
                    filename="large_file.dat",
                    dirname=str(temp_path),
                    content="",
                    extension=".dat",
                    size=large_file_size,  # This is the critical test
                    modified=datetime.now(),
                    is_directory="false",
                    hash="test_hash"
                )
            
            print("✅ Successfully indexed file with large size!")
            
            # Verify we can search for it
            with indexer.ix.searcher() as searcher:
                results = list(searcher.documents(filename="large_file.dat"))
                if results:
                    result = results[0]
                    stored_size = result['size']
                    print(f"✅ Retrieved file size: {stored_size:,} bytes")
                    if stored_size == large_file_size:
                        print("✅ File size matches! 64-bit support is working.")
                        return True
                    else:
                        print(f"❌ File size mismatch: expected {large_file_size}, got {stored_size}")
                        return False
                else:
                    print("❌ Could not find the indexed file")
                    return False
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

if __name__ == "__main__":
    success = test_large_file_size()
    if success:
        print("\n🎉 Large file size support test PASSED!")
    else:
        print("\n💥 Large file size support test FAILED!")
        exit(1)
