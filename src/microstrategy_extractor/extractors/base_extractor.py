"""Base extractor with common functionality and cache management."""

from pathlib import Path
from typing import Optional, Any
from bs4 import BeautifulSoup

from microstrategy_extractor.cache import CacheManager, MemoryCache
from microstrategy_extractor.parsers.base_parser import parse_html_file
from microstrategy_extractor.utils.logger import get_logger
from microstrategy_extractor.config.settings import Config

logger = get_logger(__name__)


class BaseExtractor:
    """Base class for all extractors with cache management."""
    
    def __init__(self, base_path: Path, cache: Optional[CacheManager] = None, 
                 config: Optional[Config] = None):
        """
        Initialize base extractor.
        
        Args:
            base_path: Base path to HTML files
            cache: Optional cache manager (creates default if not provided)
            config: Optional configuration object
        """
        self.base_path = Path(base_path)
        
        # Use provided cache or create default
        if cache is None:
            cache_size = config.cache_size_limit if config else 1000
            cache = MemoryCache(max_size=cache_size)
        self.cache = cache
        
        # Store config
        self.config = config
    
    def get_parsed_file(self, file_path: str) -> BeautifulSoup:
        """
        Get parsed HTML file, using cache if available.
        
        Args:
            file_path: File path (can include anchor, e.g., "file.html#anchor")
            
        Returns:
            BeautifulSoup object
        """
        # Extract just the file path without anchor
        file_path_only = file_path.split('#')[0]
        
        # Build full path
        if Path(file_path_only).is_absolute():
            full_path = Path(file_path_only)
        else:
            full_path = self.base_path / file_path_only
        
        # Use cache
        return self.cache.get_or_compute(
            str(full_path),
            lambda: parse_html_file(full_path),
            namespace="files"
        )
    
    def get_html_file_path(self, file_key: str) -> Path:
        """
        Get full path to a standard HTML file.
        
        Args:
            file_key: Key in HTML files (e.g., 'documento', 'metrica')
            
        Returns:
            Full path to the file
        """
        if self.config:
            return self.config.get_html_file_path(file_key)
        
        # Fallback to locale-based names if no config
        from microstrategy_extractor.i18n import get_locale
        locale = get_locale()
        file_map = {
            'documento': locale.html_files.documento,
            'relatorio': locale.html_files.relatorio,
            'cubo_inteligente': locale.html_files.cubo_inteligente,
            'atalho': locale.html_files.atalho,
            'metrica': locale.html_files.metrica,
            'fato': locale.html_files.fato,
            'funcao': locale.html_files.funcao,
            'atributo': locale.html_files.atributo,
            'tabela_logica': locale.html_files.tabela_logica,
            'pasta': locale.html_files.pasta,
        }
        
        filename = file_map.get(file_key)
        if not filename:
            raise ValueError(f"Unknown HTML file key: {file_key}")
        
        return self.base_path / filename
    
    def clear_cache(self, namespace: Optional[str] = None):
        """
        Clear cache.
        
        Args:
            namespace: Specific namespace or None for all
        """
        self.cache.clear(namespace)
        logger.debug(f"Cache cleared: {namespace or 'all namespaces'}")
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        if hasattr(self.cache, 'get_stats'):
            return self.cache.get_stats()
        return {'total': self.cache.get_size()}

