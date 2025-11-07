"""Base HTML parsing utilities for MicroStrategy documentation."""

from pathlib import Path
from typing import Optional
from bs4 import BeautifulSoup, Comment

from microstrategy_extractor.core.constants import Encodings
from microstrategy_extractor.core.exceptions import ParsingError, MissingFileError
from microstrategy_extractor.utils.logger import get_logger

logger = get_logger(__name__)


def parse_html_file(file_path: Path) -> BeautifulSoup:
    """
    Parse an HTML file and return BeautifulSoup object.
    
    Tries multiple encodings to handle files with encoding issues.
    
    Args:
        file_path: Path to HTML file
        
    Returns:
        BeautifulSoup object
        
    Raises:
        MissingFileError: If file doesn't exist
        ParsingError: If parsing fails completely
    """
    if not file_path.exists():
        raise MissingFileError(file_path, "Required for parsing")
    
    # Try different encodings in order of likelihood
    for encoding in Encodings.PREFERRED_ORDER:
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            # If we got here, the encoding worked
            return BeautifulSoup(content, 'html.parser')
        except (UnicodeDecodeError, LookupError):
            continue
        except Exception as e:
            logger.warning(f"Error reading {file_path} with encoding {encoding}: {e}")
            continue
    
    # Fallback: use utf-8 with errors='ignore'
    try:
        with open(file_path, 'r', encoding=Encodings.FALLBACK, errors='ignore') as f:
            content = f.read()
        return BeautifulSoup(content, 'html.parser')
    except Exception as e:
        raise ParsingError(f"Failed to parse HTML file: {e}", file_path)


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
    for link in cell.find_all('a'):
        text = link.get_text(strip=True)
        href = link.get('href', '')
        
        if not text or not href:
            continue
        
    # Extract ID from href if present
    import re
    from microstrategy_extractor.core.constants import RegexPatterns
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

