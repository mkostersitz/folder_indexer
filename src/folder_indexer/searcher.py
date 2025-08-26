"""
Search functionality for querying indexed files and directories.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from whoosh import index, qparser
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.query import Query, Term, And, Or, Wildcard
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .config import Config, get_index_dir


class SearchResult:
    """Represents a single search result."""
    
    def __init__(self, doc: Dict[str, Any], score: float = 0.0):
        self.path = doc.get('path', '')
        self.filename = doc.get('filename', '')
        self.dirname = doc.get('dirname', '')
        self.content = doc.get('content', '')
        self.extension = doc.get('extension', '')
        self.size = doc.get('size', 0)
        self.modified = doc.get('modified')
        self.is_directory = doc.get('is_directory', 'false') == 'true'
        self.hash = doc.get('hash', '')
        self.score = score
    
    def __repr__(self):
        return f"SearchResult(path='{self.path}', score={self.score})"


class FileSearcher:
    """Handles searching through indexed files and directories."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.console = Console()
        self.index_dir = get_index_dir()
        self._open_index()
    
    def _open_index(self):
        """Open the search index."""
        if not index.exists_in(str(self.index_dir)):
            raise FileNotFoundError("No search index found. Please index some directories first.")
        self.ix = index.open_dir(str(self.index_dir))
    
    def search(
        self,
        query: str,
        pattern: Optional[str] = None,
        content_search: bool = False,
        file_type: Optional[str] = None,
        max_size: Optional[int] = None,
        min_size: Optional[int] = None,
        modified_after: Optional[datetime] = None,
        modified_before: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Search for files and directories.
        
        Args:
            query: Search query string
            pattern: File pattern (e.g., '*.py')
            content_search: Whether to search in file contents
            file_type: 'file' or 'directory' to filter by type
            max_size: Maximum file size in bytes
            min_size: Minimum file size in bytes
            modified_after: Only files modified after this date
            modified_before: Only files modified before this date
            limit: Maximum number of results to return
        """
        limit = limit or self.config.search.max_results
        
        with self.ix.searcher() as searcher:
            queries = []
            
            # Build the main query
            if query:
                if content_search:
                    # Search in both filename and content
                    parser = MultifieldParser(['filename', 'content'], self.ix.schema)
                else:
                    # Search only in filename
                    parser = QueryParser('filename', self.ix.schema)
                
                try:
                    main_query = parser.parse(query)
                    queries.append(main_query)
                except Exception:
                    # Fallback to wildcard search if parsing fails
                    queries.append(Wildcard('filename', f'*{query}*'))
            
            # Add pattern filter
            if pattern:
                pattern_query = self._build_pattern_query(pattern)
                if pattern_query:
                    queries.append(pattern_query)
            
            # Add file type filter
            if file_type:
                if file_type.lower() == 'file':
                    queries.append(Term('is_directory', 'false'))
                elif file_type.lower() == 'directory':
                    queries.append(Term('is_directory', 'true'))
            
            # Combine all queries
            if queries:
                combined_query = And(queries) if len(queries) > 1 else queries[0]
            else:
                # If no specific query, search all
                combined_query = qparser.Every()
            
            # Execute search
            results = searcher.search(combined_query, limit=limit)
            
            # Convert to SearchResult objects and apply additional filters
            search_results = []
            for result in results:
                result_obj = SearchResult(dict(result), result.score)
                
                # Apply size filters
                if max_size is not None and result_obj.size > max_size:
                    continue
                if min_size is not None and result_obj.size < min_size:
                    continue
                
                # Apply date filters
                if modified_after and result_obj.modified:
                    if result_obj.modified < modified_after:
                        continue
                if modified_before and result_obj.modified:
                    if result_obj.modified > modified_before:
                        continue
                
                search_results.append(result_obj)
            
            return search_results
    
    def _build_pattern_query(self, pattern: str) -> Optional[Query]:
        """Build a query for file pattern matching."""
        if not pattern:
            return None
        
        # Convert shell-style wildcards to Whoosh wildcards
        # This is a simple conversion - could be made more sophisticated
        whoosh_pattern = pattern.replace('*', '*').replace('?', '?')
        
        if '.' in pattern and not pattern.startswith('.'):
            # Likely a file extension pattern
            return Wildcard('filename', whoosh_pattern)
        else:
            # General filename pattern
            return Wildcard('filename', whoosh_pattern)
    
    def search_content(self, query: str, limit: Optional[int] = None) -> List[SearchResult]:
        """Search specifically in file contents."""
        return self.search(query, content_search=True, limit=limit)
    
    def find_by_extension(self, extension: str, limit: Optional[int] = None) -> List[SearchResult]:
        """Find files by extension."""
        if not extension.startswith('.'):
            extension = '.' + extension
        
        with self.ix.searcher() as searcher:
            query = Term('extension', extension.lower())
            results = searcher.search(query, limit=limit or self.config.search.max_results)
            return [SearchResult(dict(result), result.score) for result in results]
    
    def find_large_files(self, min_size_mb: float = 100, limit: Optional[int] = None) -> List[SearchResult]:
        """Find large files above a certain size."""
        min_bytes = int(min_size_mb * 1024 * 1024)
        return self.search('', min_size=min_bytes, file_type='file', limit=limit)
    
    def find_recent_files(self, days: int = 7, limit: Optional[int] = None) -> List[SearchResult]:
        """Find recently modified files."""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        return self.search('', modified_after=cutoff_date, file_type='file', limit=limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed content."""
        with self.ix.searcher() as searcher:
            # Count files vs directories
            file_query = Term('is_directory', 'false')
            dir_query = Term('is_directory', 'true')
            
            file_results = searcher.search(file_query, limit=None)
            dir_results = searcher.search(dir_query, limit=None)
            
            file_count = len(file_results)
            dir_count = len(dir_results)
            total_docs = file_count + dir_count
            
            # Get total size
            total_size = sum(result.get('size', 0) for result in file_results)
            
            return {
                'total_documents': total_docs,
                'file_count': file_count,
                'directory_count': dir_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
    
    def display_results(self, results: List[SearchResult], show_content: bool = False):
        """Display search results in a formatted table."""
        if not results:
            self.console.print("[yellow]No results found.[/yellow]")
            return
        
        table = Table(title=f"Search Results ({len(results)} found)")
        table.add_column("Path", style="cyan", no_wrap=False)
        table.add_column("Type", style="green")
        table.add_column("Size", style="yellow", justify="right")
        table.add_column("Modified", style="blue")
        
        if show_content:
            table.add_column("Content Preview", style="dim")
        
        for result in results:
            # Format file size
            if result.size > 0:
                if result.size > 1024 * 1024:
                    size_str = f"{result.size / (1024 * 1024):.1f} MB"
                elif result.size > 1024:
                    size_str = f"{result.size / 1024:.1f} KB"
                else:
                    size_str = f"{result.size} B"
            else:
                size_str = "-"
            
            # Format modification time
            if result.modified:
                if isinstance(result.modified, datetime):
                    mod_time = result.modified.strftime("%Y-%m-%d %H:%M")
                else:
                    mod_time = datetime.fromtimestamp(result.modified).strftime("%Y-%m-%d %H:%M")
            else:
                mod_time = "-"
            
            # File type
            file_type = "📁 DIR" if result.is_directory else "📄 FILE"
            
            row = [result.path, file_type, size_str, mod_time]
            
            if show_content and result.content:
                # Show first 100 characters of content
                content_preview = result.content[:100].replace('\n', ' ').strip()
                if len(result.content) > 100:
                    content_preview += "..."
                row.append(content_preview)
            elif show_content:
                row.append("-")
            
            table.add_row(*row)
        
        self.console.print(table)
