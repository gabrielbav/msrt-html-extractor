"""Base HTML parsing utilities for MicroStrategy documentation."""

from pathlib import Path
from typing import Optional, Dict
from threading import Lock
from bs4 import BeautifulSoup, Comment

from microstrategy_extractor.core.constants import Encodings
from microstrategy_extractor.core.exceptions import ParsingError, MissingFileError
from microstrategy_extractor.utils.logger import get_logger

logger = get_logger(__name__)

# GLOBAL cache shared across ALL extractor instances and threads
# This dramatically reduces parsing overhead by caching common files
_GLOBAL_HTML_CACHE: Dict[str, BeautifulSoup] = {}
_CACHE_STATS = {'hits': 0, 'misses': 0}
_HTML_CACHE_LOCK = Lock()
_HTML_STATS_LOCK = Lock()


def parse_html_file(file_path: Path) -> BeautifulSoup:
    """
    Parse an HTML file with global caching.
    
    This cache is shared across ALL extractor instances and threads,
    significantly reducing parsing overhead.
    
    Args:
        file_path: Path to HTML file
        
    Returns:
        BeautifulSoup object (cached)
        
    Raises:
        MissingFileError: If file doesn't exist
        ParsingError: If parsing fails completely
    """
    if not file_path.exists():
        raise MissingFileError(file_path, "Required for parsing")
    
    file_path_str = str(file_path)
    
    # Check global cache with thread-safe read
    with _HTML_CACHE_LOCK:
        if file_path_str in _GLOBAL_HTML_CACHE:
            with _HTML_STATS_LOCK:
                _CACHE_STATS['hits'] += 1
            return _GLOBAL_HTML_CACHE[file_path_str]
    
    with _HTML_STATS_LOCK:
        _CACHE_STATS['misses'] += 1
    
    # Try different encodings in order of likelihood
    parsed = None
    for encoding in Encodings.PREFERRED_ORDER:
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            # If we got here, the encoding worked
            parsed = BeautifulSoup(content, 'html.parser')
            break
        except (UnicodeDecodeError, LookupError):
            continue
        except Exception as e:
            logger.warning(f"Error reading {file_path} with encoding {encoding}: {e}")
            continue
    
    # Fallback: use utf-8 with errors='ignore'
    if parsed is None:
        try:
            with open(file_path, 'r', encoding=Encodings.FALLBACK, errors='ignore') as f:
                content = f.read()
            parsed = BeautifulSoup(content, 'html.parser')
        except Exception as e:
            raise ParsingError(f"Failed to parse HTML file: {e}", file_path)
    
    # Store in global cache with thread-safe write
    with _HTML_CACHE_LOCK:
        _GLOBAL_HTML_CACHE[file_path_str] = parsed
    
    return parsed


def find_object_section(soup: BeautifulSoup, object_name: str, 
                       anchor: Optional[str] = None) -> Optional[BeautifulSoup]:
    """
    Find an object section by name using [OBJECT: ...] comment markers or anchor.
    
    Returns a BeautifulSoup fragment containing only the specific object section,
    bounded by the object's anchor and the next object marker (OBJECT comment or next anchor).
    
    Args:
        soup: BeautifulSoup object to search
        object_name: Name of object to find
        anchor: Optional anchor ID to search for
        
    Returns:
        BeautifulSoup fragment or None if not found
    """
    # If anchor is provided, try to find by anchor first
    if anchor:
        anchor_tag = soup.find('a', {'name': anchor})
        if anchor_tag:
            logger.debug(f"Found anchor tag for: {anchor}")
            
            # Find the parent TR that contains this anchor (each object is in a TR)
            parent_tr = anchor_tag
            while parent_tr and parent_tr.name != 'tr':
                parent_tr = parent_tr.parent
            
            if parent_tr:
                # Return just this TR which contains the entire object section
                return parent_tr
    
    # Search for comments containing the object name
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment_text = str(comment)
        if f'[OBJECT: {object_name}]' in comment_text or f'[OBJECT: {object_name} ' in comment_text:
            # Find the parent table that contains this object
            parent = comment.parent
            while parent and parent.name != 'table':
                parent = parent.parent
            if parent:
                # Return the section starting from this table
                return parent.find_parent('table') or parent
    
    return None


def find_section_by_header(soup: BeautifulSoup, header_text: str, 
                          anchor: Optional[str] = None,
                          class_name: Optional[str] = None) -> Optional[BeautifulSoup]:
    """
    Find a section by its header text.
    
    Args:
        soup: BeautifulSoup object to search
        header_text: Text to search for in headers
        anchor: Optional anchor to limit search scope
        class_name: Optional CSS class to filter by
        
    Returns:
        BeautifulSoup fragment starting from header or None
    """
    search_area = soup
    
    # If anchor provided, limit search to section after anchor
    if anchor:
        anchor_tag = soup.find('a', {'name': anchor})
        if anchor_tag:
            search_area = anchor_tag.find_parent('table') or anchor_tag.parent
    
    # Search for header
    if class_name:
        headers = search_area.find_all(class_=class_name)
    else:
        headers = search_area.find_all(['td', 'th'])
    
    for header in headers:
        if header_text in header.get_text(strip=True):
            return header
    
    return None


def extract_table_data(table: BeautifulSoup, skip_header: bool = True) -> list[list[str]]:
    """
    Extract data from an HTML table.
    
    Args:
        table: BeautifulSoup table element
        skip_header: Whether to skip the first row
        
    Returns:
        List of rows, each row is a list of cell contents
    """
    rows = []
    tr_elements = table.find_all('tr')
    
    start_index = 1 if skip_header and len(tr_elements) > 1 else 0
    
    for tr in tr_elements[start_index:]:
        cells = tr.find_all(['td', 'th'])
        row = [cell.get_text(strip=True) for cell in cells]
        if any(row):  # Only add non-empty rows
            rows.append(row)
    
    return rows


def get_table_headers(table: BeautifulSoup) -> list[str]:
    """
    Extract column headers from a table.
    
    Args:
        table: BeautifulSoup table element
        
    Returns:
        List of header texts
    """
    header_row = table.find('tr')
    if not header_row:
        return []
    
    headers = header_row.find_all(['td', 'th'])
    return [h.get_text(strip=True) for h in headers]


def find_next_table_after(element: BeautifulSoup, 
                          skip_empty: bool = True,
                          max_search: int = 10) -> Optional[BeautifulSoup]:
    """
    Find the next table element after a given element.
    
    Args:
        element: Starting element
        skip_empty: Whether to skip tables with no data rows
        max_search: Maximum number of tables to check
        
    Returns:
        Next table element or None
    """
    current = element
    checked = 0
    
    while current and checked < max_search:
        current = current.find_next('table')
        if not current:
            break
        
        checked += 1
        
        if skip_empty:
            rows = current.find_all('tr')
            if rows and len(rows) > 1:  # Has header + data
                return current
        else:
            return current
    
    return None


def extract_links_from_cell(cell: BeautifulSoup) -> list[dict]:
    """
    Extract all links from a table cell.
    
    Args:
        cell: BeautifulSoup cell element
        
    Returns:
        List of dicts with 'text', 'href', 'id' keys
    """
    links = []
    import re
    from microstrategy_extractor.core.constants import RegexPatterns
    
    for link in cell.find_all('a'):
        text = link.get_text(strip=True)
        href = link.get('href', '')
        
        if not text or not href:
            continue
        
        # Extract ID from href if present
        object_id = None
        match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
        if match:
            object_id = match.group(1)
        elif '#' in href:
            object_id = href.split('#')[1]
        
        links.append({
            'text': text,
            'href': href,
            'id': object_id
        })
    
    return links


def is_empty_table(table: BeautifulSoup) -> bool:
    """
    Check if a table is empty (no meaningful content).
    
    Args:
        table: BeautifulSoup table element
        
    Returns:
        True if table is empty
    """
    rows = table.find_all('tr')
    if not rows:
        return True
    
    # Check if any row has meaningful text
    for row in rows:
        cells = row.find_all(['td', 'th'])
        for cell in cells:
            text = cell.get_text(strip=True)
            if text and len(text) > 0:
                return False
    
    return True


def preload_common_files(base_path: Path) -> None:
    """Pre-load commonly used index files into global cache.
    
    These files are accessed by almost every report extraction,
    so pre-loading them saves massive time.
    
    Args:
        base_path: Base directory containing HTML files
    """
    from microstrategy_extractor.i18n import get_locale
    locale = get_locale()
    
    common_files = [
        locale.html_files.metrica,
        locale.html_files.atributo,
        locale.html_files.fato,
        locale.html_files.funcao,
        locale.html_files.tabela_logica,
        locale.html_files.cubo_inteligente,
        locale.html_files.relatorio,
        locale.html_files.atalho,
        locale.html_files.documento,
    ]
    
    logger.info(f"Pre-loading {len(common_files)} common index files into memory...")
    loaded_count = 0
    for filename in common_files:
        file_path = base_path / filename
        if file_path.exists():
            parse_html_file(file_path)
            loaded_count += 1
            logger.info(f"  ✓ Cached {filename}")
        else:
            logger.debug(f"  ✗ Skipped {filename} (not found)")
    
    logger.info(f"Pre-loaded {loaded_count}/{len(common_files)} files into global cache")


def preload_all_html_files(base_path: Path, max_files: int = None) -> None:
    """Pre-load ALL HTML files in the directory into global cache.
    
    This is an aggressive caching strategy that loads all HTML files
    into memory at startup. Uses 4-8GB RAM but provides 2-3x speedup
    by eliminating all file I/O during extraction.
    
    Args:
        base_path: Base directory containing HTML files
        max_files: Optional limit on number of files to cache (for testing)
    """
    import time
    from glob import glob
    
    start_time = time.time()
    logger.info("=== AGGRESSIVE CACHING: Pre-loading ALL HTML files ===")
    
    # Find all HTML files recursively
    html_pattern = str(base_path / "**" / "*.html")
    all_html_files = glob(html_pattern, recursive=True)
    
    total_files = len(all_html_files)
    if max_files:
        all_html_files = all_html_files[:max_files]
        logger.info(f"Found {total_files} HTML files, loading first {max_files}...")
    else:
        logger.info(f"Found {total_files} HTML files to pre-cache...")
    
    # Pre-load all files with progress indication
    loaded_count = 0
    failed_count = 0
    last_progress = 0
    
    for i, file_path in enumerate(all_html_files, 1):
        try:
            parse_html_file(Path(file_path))
            loaded_count += 1
            
            # Show progress every 10%
            progress = (i * 100) // len(all_html_files)
            if progress >= last_progress + 10:
                elapsed = time.time() - start_time
                rate = loaded_count / elapsed if elapsed > 0 else 0
                eta = (len(all_html_files) - i) / rate if rate > 0 else 0
                logger.info(f"  Progress: {progress}% ({i}/{len(all_html_files)}) - "
                           f"{rate:.0f} files/sec - ETA: {eta:.0f}s")
                last_progress = progress
        except Exception as e:
            failed_count += 1
            logger.debug(f"  Failed to cache {file_path}: {e}")
    
    elapsed = time.time() - start_time
    cache_size_mb = sum(len(str(soup)) for soup in _GLOBAL_HTML_CACHE.values()) / (1024 * 1024)
    
    logger.info(f"✓ Pre-cached {loaded_count} HTML files in {elapsed:.1f}s "
               f"({loaded_count/elapsed:.0f} files/sec)")
    logger.info(f"  Cache size: {len(_GLOBAL_HTML_CACHE)} files, ~{cache_size_mb:.0f}MB in memory")
    if failed_count > 0:
        logger.warning(f"  Failed to cache {failed_count} files (see debug log)")


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics for monitoring performance.
    
    Returns:
        Dict with 'hits', 'misses', 'size', and 'hit_rate'
    """
    total = _CACHE_STATS['hits'] + _CACHE_STATS['misses']
    hit_rate = (_CACHE_STATS['hits'] / total * 100) if total > 0 else 0
    
    return {
        'hits': _CACHE_STATS['hits'],
        'misses': _CACHE_STATS['misses'],
        'size': len(_GLOBAL_HTML_CACHE),
        'hit_rate': round(hit_rate, 2)
    }

