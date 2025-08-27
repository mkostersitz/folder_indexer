#!/usr/bin/env python3
"""
Test large file support and filenames-only indexing functionality.
"""

import sys
from pathlib import Path
# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tempfile
from datetime import datetime
from folder_indexer.indexer import DirectoryIndexer
from folder_indexer.config import Config


def test_filenames_only_indexing():
    """Test that filenames-only indexing works correctly."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files with content
        test_file = temp_path / "test_file.txt"
        test_file.write_text("This is test content that should be skipped in filenames-only mode")
        
        # Create a test indexer
        config = Config()
        indexer = DirectoryIndexer(config)
        
        # Test filenames-only indexing
        count = indexer.index_directory(temp_path, show_progress=False, filenames_only=True)
        
        print(f"Indexed {count} items")
        assert count >= 1  # Should index at least the 1 file we created
        
        # Verify that the file was indexed but without content
        with indexer.ix.searcher() as searcher:
            # List all documents to see what was indexed
            all_docs = list(searcher.documents())
            print(f"Found {len(all_docs)} documents in index")
            
            # Find our test file
            txt_results = [doc for doc in all_docs if doc.get('filename') == 'test_file.txt']
            print(f"Found {len(txt_results)} test_file.txt matches")
            
            if txt_results:
                result = txt_results[0]
                print(f"Content length: {len(result.get('content', ''))}")
                print(f"Filename: {result.get('filename')}")
                
                # Content should be empty in filenames-only mode
                assert result['content'] == "", f"Expected empty content, got: {result['content'][:50]}..."
                
                # But filename should still be populated
                assert result['filename'] == "test_file.txt"
        
        print("✅ Filenames-only indexing test passed!")
        return True

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
    # Run both tests
    success1 = test_filenames_only_indexing()
    success2 = test_large_file_size()
    
    if success1 and success2:
        print("\n🎉 All tests PASSED!")
    else:
        print("\n💥 Some tests FAILED!")
        exit(1)
