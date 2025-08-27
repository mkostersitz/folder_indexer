"""
Command-line interface for the folder indexer.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import click
from rich.console import Console

from . import __version__
from .config import load_config
from .indexer import DirectoryIndexer
from .searcher import FileSearcher
from .watcher import DirectoryWatcher


console = Console()


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    """Folder Indexer - Fast search for your filesystem."""
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config()


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--no-progress', is_flag=True, help='Disable progress display')
@click.option('--filenames-only', is_flag=True, help='Index only filenames and metadata (skip content extraction for faster indexing)')
@click.option('--verbose-errors', is_flag=True, help='Show detailed error messages for files that cannot be indexed')
@click.pass_context
def index(ctx, directory: Path, no_progress: bool, filenames_only: bool, verbose_errors: bool):
    """Index a directory structure for fast searching."""
    config = ctx.obj['config']
    
    # Override the verbose_errors setting if specified
    if verbose_errors:
        config.indexing.verbose_errors = True
    
    indexer = DirectoryIndexer(config)
    
    try:
        count = indexer.index_directory(directory, show_progress=not no_progress, filenames_only=filenames_only)
        mode = "filenames only" if filenames_only else "with content"
        console.print(f"[green]v Successfully indexed {count} items from {directory} ({mode})[/green]")
    except Exception as e:
        console.print(f"[red]x Error indexing directory: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('query', required=False)
@click.option('--pattern', '-p', help='File pattern to match (e.g., *.py)')
@click.option('--content', '-c', is_flag=True, help='Search in file contents')
@click.option('--type', 'file_type', type=click.Choice(['file', 'directory']), help='Filter by type')
@click.option('--max-size', type=int, help='Maximum file size in MB')
@click.option('--min-size', type=int, help='Minimum file size in KB')
@click.option('--modified-after', type=click.DateTime(), help='Files modified after this date')
@click.option('--modified-before', type=click.DateTime(), help='Files modified before this date')
@click.option('--limit', '-l', type=int, help='Maximum number of results')
@click.option('--show-content', is_flag=True, help='Show content preview in results')
@click.pass_context
def search(ctx, query: Optional[str], pattern: Optional[str], content: bool, 
          file_type: Optional[str], max_size: Optional[int], min_size: Optional[int],
          modified_after: Optional[datetime], modified_before: Optional[datetime],
          limit: Optional[int], show_content: bool):
    """Search indexed files and directories."""
    if not query and not pattern:
        console.print("[red]Please provide a search query or pattern[/red]")
        sys.exit(1)
    
    config = ctx.obj['config']
    
    try:
        searcher = FileSearcher(config)
        
        # Convert size units
        max_size_bytes = max_size * 1024 * 1024 if max_size else None
        min_size_bytes = min_size * 1024 if min_size else None
        
        results = searcher.search(
            query or '',
            pattern=pattern,
            content_search=content,
            file_type=file_type,
            max_size=max_size_bytes,
            min_size=min_size_bytes,
            modified_after=modified_after,
            modified_before=modified_before,
            limit=limit
        )
        
        searcher.display_results(results, show_content=show_content)
        
    except FileNotFoundError:
        console.print("[red]No search index found. Please index some directories first using 'folder-indexer index <directory>'[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Search error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option('--recursive/--no-recursive', default=True, help='Watch subdirectories recursively')
@click.pass_context
def watch(ctx, directory: Path, recursive: bool):
    """Watch a directory for changes and update the index automatically."""
    config = ctx.obj['config']
    watcher = DirectoryWatcher(config)
    
    # First, make sure the directory is indexed
    indexer = DirectoryIndexer(config)
    console.print(f"[yellow]Ensuring {directory} is indexed...[/yellow]")
    indexer.index_directory(directory)
    
    # Start watching
    if watcher.add_watch(directory, recursive=recursive):
        console.print(f"[green]Watching {directory} for changes. Press Ctrl+C to stop.[/green]")
        try:
            watcher.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping watcher...[/yellow]")
        finally:
            watcher.stop()
    else:
        sys.exit(1)


@cli.command()
@click.pass_context
def list(ctx):
    """List all indexed directories."""
    config = ctx.obj['config']
    
    try:
        indexer = DirectoryIndexer(config)
        directories = indexer.get_indexed_directories()
        
        if not directories:
            console.print("[yellow]No directories are currently indexed.[/yellow]")
        else:
            console.print(f"[green]Found {len(directories)} indexed directories:[/green]")
            for directory in directories:
                path = Path(directory)
                status = "✓" if path.exists() else "✗"
                console.print(f"  {status} {directory}")
    except Exception as e:
        console.print(f"[red]Error listing directories: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(path_type=Path))
@click.pass_context
def remove(ctx, directory: Path):
    """Remove a directory from the index."""
    config = ctx.obj['config']
    indexer = DirectoryIndexer(config)
    
    try:
        count = indexer.remove_directory(directory)
        if count > 0:
            console.print(f"[green]✓ Removed {count} items for directory {directory}[/green]")
        else:
            console.print(f"[yellow]No items found for directory {directory}[/yellow]")
    except Exception as e:
        console.print(f"[red]Error removing directory: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def rebuild(ctx):
    """Rebuild the entire search index."""
    config = ctx.obj['config']
    indexer = DirectoryIndexer(config)
    
    console.print("[yellow]Rebuilding search index...[/yellow]")
    try:
        count = indexer.rebuild_index()
        console.print(f"[green]✓ Rebuilt index with {count} total items[/green]")
    except Exception as e:
        console.print(f"[red]Error rebuilding index: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show statistics about the indexed content."""
    config = ctx.obj['config']
    
    try:
        searcher = FileSearcher(config)
        stats = searcher.get_stats()
        
        console.print("[bold]Index Statistics:[/bold]")
        console.print(f"  Total documents: {stats['total_documents']:,}")
        console.print(f"  Files: {stats['file_count']:,}")
        console.print(f"  Directories: {stats['directory_count']:,}")
        console.print(f"  Total size: {stats['total_size_mb']:,} MB")
        
    except FileNotFoundError:
        console.print("[red]No search index found. Please index some directories first.[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error getting statistics: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--extension', '-e', help='Find files by extension')
@click.option('--large-files', type=float, help='Find files larger than N MB')
@click.option('--recent', type=int, help='Find files modified in last N days')
@click.option('--limit', '-l', type=int, default=20, help='Maximum number of results')
@click.pass_context
def find(ctx, extension: Optional[str], large_files: Optional[float], 
         recent: Optional[int], limit: int):
    """Quick find commands for common searches."""
    config = ctx.obj['config']
    
    try:
        searcher = FileSearcher(config)
        
        if extension:
            results = searcher.find_by_extension(extension, limit=limit)
            console.print(f"[bold]Files with extension '.{extension}':[/bold]")
        elif large_files:
            results = searcher.find_large_files(min_size_mb=large_files, limit=limit)
            console.print(f"[bold]Files larger than {large_files} MB:[/bold]")
        elif recent:
            results = searcher.find_recent_files(days=recent, limit=limit)
            console.print(f"[bold]Files modified in last {recent} days:[/bold]")
        else:
            console.print("[red]Please specify one of: --extension, --large-files, or --recent[/red]")
            sys.exit(1)
        
        searcher.display_results(results)
        
    except FileNotFoundError:
        console.print("[red]No search index found. Please index some directories first.[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
