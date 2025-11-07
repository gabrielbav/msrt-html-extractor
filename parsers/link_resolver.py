"""Generic link resolution for MicroStrategy HTML documentation."""

import re
from pathlib import Path
from typing import Optional, Dict, Callable
from bs4 import BeautifulSoup

from constants import HTMLClasses, RegexPatterns
from utils.text_normalizer import TextNormalizer
from exceptions import LinkResolutionError, ParsingError


class LinkResult(Dict[str, str]):
    """Type for link resolution results."""
    pass


class LinkResolver:
    """Generic resolver for finding objects in HTML index files."""
    
    def __init__(self, index_path: Path, object_type: str):
        """
        Initialize link resolver.
        
        Args:
            index_path: Path to HTML index file
            object_type: Type of object being resolved (e.g., "Metric", "Attribute")
        """
        self.index_path = index_path
        self.object_type = object_type
        self._soup: Optional[BeautifulSoup] = None
    
    def _ensure_parsed(self):
        """Ensure HTML file is parsed (lazy loading)."""
        if self._soup is None:
            if not self.index_path.exists():
                raise LinkResolutionError(
                    self.object_type,
                    index_file=self.index_path
                )
            
            # Import here to avoid circular dependency
            from parsers.base_parser import parse_html_file
            self._soup = parse_html_file(self.index_path)
    
    def find_by_id(self, object_id: str) -> Optional[LinkResult]:
        """
        Find object by ID (most accurate method).
        
        Args:
            object_id: Object ID to find
            
        Returns:
            LinkResult with name, file, anchor, href or None
        """
        self._ensure_parsed()
        
        # Search for links with matching anchor or placeholder ID
        for link in self._soup.find_all('a', class_=HTMLClasses.MAINBODY):
            href = link.get('href', '')
            
            # Check anchor in href (format: file.html#ID)
            parts = href.split('#')
            anchor = parts[1] if len(parts) > 1 else ''
            
            if anchor.upper() == object_id.upper():
                return LinkResult({
                    'name': link.get_text(strip=True),
                    'file': parts[0] if parts else '',
                    'anchor': anchor,
                    'href': href,
                    'id': anchor
                })
            
            # Check placeholder format [$$$$ID$$$$]
            if '[$$$$' in href:
                match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                if match and match.group(1).upper() == object_id.upper():
                    return LinkResult({
                        'name': link.get_text(strip=True),
                        'file': parts[0] if parts else '',
                        'anchor': anchor or match.group(1),
                        'href': href,
                        'id': match.group(1)
                    })
        
        return None
    
    def find_by_name(self, object_name: str, 
                    normalize_fn: Optional[Callable[[str], str]] = None) -> Optional[LinkResult]:
        """
        Find object by name with optional custom normalization.
        
        Args:
            object_name: Name of object to find
            normalize_fn: Optional function to normalize text for comparison
            
        Returns:
            LinkResult with name, file, anchor, href or None
        """
        self._ensure_parsed()
        
        if normalize_fn is None:
            normalize_fn = TextNormalizer.normalize_for_matching
        
        object_name_norm = normalize_fn(object_name)
        
        # Try exact match first
        for link in self._soup.find_all('a', class_=HTMLClasses.MAINBODY):
            link_text = link.get_text(strip=True)
            
            if link_text == object_name:
                href = link.get('href', '')
                parts = href.split('#')
                anchor = parts[1] if len(parts) > 1 else ''
                
                # Extract ID from href if available
                object_id = None
                if '[$$$$' in href:
                    match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                    if match:
                        object_id = match.group(1)
                
                return LinkResult({
                    'name': link_text,
                    'file': parts[0] if parts else '',
                    'anchor': anchor or object_id or '',
                    'href': href,
                    'id': object_id or anchor
                })
        
        # Try normalized match
        for link in self._soup.find_all('a', class_=HTMLClasses.MAINBODY):
            link_text = link.get_text(strip=True)
            link_text_norm = normalize_fn(link_text)
            
            if link_text_norm == object_name_norm:
                href = link.get('href', '')
                parts = href.split('#')
                anchor = parts[1] if len(parts) > 1 else ''
                
                object_id = None
                if '[$$$$' in href:
                    match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                    if match:
                        object_id = match.group(1)
                
                return LinkResult({
                    'name': link_text,
                    'file': parts[0] if parts else '',
                    'anchor': anchor or object_id or '',
                    'href': href,
                    'id': object_id or anchor
                })
        
        # Try partial/fuzzy match
        best_match = TextNormalizer.find_best_match(
            object_name,
            [link.get_text(strip=True) for link in self._soup.find_all('a', class_=HTMLClasses.MAINBODY)]
        )
        
        if best_match:
            for link in self._soup.find_all('a', class_=HTMLClasses.MAINBODY):
                if link.get_text(strip=True) == best_match:
                    href = link.get('href', '')
                    parts = href.split('#')
                    anchor = parts[1] if len(parts) > 1 else ''
                    
                    object_id = None
                    if '[$$$$' in href:
                        match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                        if match:
                            object_id = match.group(1)
                    
                    return LinkResult({
                        'name': link.get_text(strip=True),
                        'file': parts[0] if parts else '',
                        'anchor': anchor or object_id or '',
                        'href': href,
                        'id': object_id or anchor
                    })
        
        return None
    
    def find_link(self, object_id: Optional[str] = None, 
                 object_name: Optional[str] = None,
                 normalize_fn: Optional[Callable[[str], str]] = None) -> Optional[LinkResult]:
        """
        Find object link by ID or name (ID takes precedence).
        
        Args:
            object_id: Optional object ID
            object_name: Optional object name
            normalize_fn: Optional normalization function
            
        Returns:
            LinkResult or None if not found
            
        Raises:
            LinkResolutionError: If neither ID nor name provided
        """
        if not object_id and not object_name:
            raise LinkResolutionError(
                self.object_type,
                object_id=object_id,
                object_name=object_name,
                index_file=self.index_path
            )
        
        # Try ID first (most accurate)
        if object_id:
            result = self.find_by_id(object_id)
            if result:
                return result
        
        # Fallback to name
        if object_name:
            result = self.find_by_name(object_name, normalize_fn)
            if result:
                return result
        
        return None
    
    def find_all(self) -> list[LinkResult]:
        """
        Find all objects in the index file.
        
        Returns:
            List of LinkResult dicts
        """
        self._ensure_parsed()
        
        results = []
        for link in self._soup.find_all('a', class_=HTMLClasses.MAINBODY):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            if not link_text or not href:
                continue
            
            parts = href.split('#')
            anchor = parts[1] if len(parts) > 1 else ''
            
            object_id = None
            if '[$$$$' in href:
                match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                if match:
                    object_id = match.group(1)
            
            results.append(LinkResult({
                'name': link_text,
                'file': parts[0] if parts else '',
                'anchor': anchor or object_id or '',
                'href': href,
                'id': object_id or anchor
            }))
        
        return results

