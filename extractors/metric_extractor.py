"""Metric extraction logic with support for simple and composite metrics."""

from pathlib import Path
from typing import Optional, Set, Dict

from extractors.base_extractor import BaseExtractor
from models import Metrica, Function, Fact, LogicTable
from parsers.metric_parser import extract_metric_definition
from parsers.fact_parser import find_fact_link, find_function_link, find_logical_table_link, extract_fact_logic_tables
from html_parser import find_metric_link
from utils.logger import get_logger
from constants import ApplicationObjects
from extractor_helpers import (
    check_circular_reference, check_metric_cache,
    extract_simple_metric_components, extract_composite_metric_components
)

logger = get_logger(__name__)


class MetricExtractor(BaseExtractor):
    """Extractor for metric details (simple and composite)."""
    
    def extract(self, metrica_name: str, metrica_file_path: str, dataset_id: str,
               metrica_id: Optional[str] = None, visited_ids: Optional[Set[str]] = None) -> Optional[Metrica]:
        """
        Extract metric details, handling both simple and composite metrics.
        
        REFACTORED: Now uses helper functions from extractor_helpers module.
        
        Args:
            metrica_name: Name of the metric
            metrica_file_path: File path with anchor
            dataset_id: ID of the dataset
            metrica_id: Optional metric ID
            visited_ids: Set of IDs being processed (circular reference detection)
            
        Returns:
            Metrica object or None
        """
        # Initialize visited_ids
        if visited_ids is None:
            visited_ids = set()
        
        # Extract metric ID if not provided
        if not metrica_id:
            parts = metrica_file_path.split('#')
            metrica_id = parts[1] if len(parts) > 1 else ''
        
        # Check for circular reference
        if check_circular_reference(metrica_id, metrica_name, visited_ids):
            return None
        
        # Add to visited set
        if metrica_id:
            visited_ids.add(metrica_id)
        
        # Check cache
        cache_key = f"{metrica_id}:{metrica_name}" if metrica_id else f"{dataset_id}:{metrica_name}"
        
        # Get metric cache dict (backward compatibility with old cache structure)
        metric_cache = self._get_metric_cache_dict()
        
        cached_metric = check_metric_cache(
            cache_key, metric_cache, dataset_id, metrica_id, visited_ids
        )
        if cached_metric:
            return cached_metric
        
        logger.debug(f"Extracting metric: {metrica_name}")
        
        # Extract file components
        parts = metrica_file_path.split('#')
        metrica_file_name = parts[0]
        metrica_anchor = parts[1] if len(parts) > 1 else ''
        
        metrica_file = self.base_path / metrica_file_name
        if not metrica_file.exists():
            logger.warning(f"Metric file not found: {metrica_file}")
            if metrica_id:
                visited_ids.discard(metrica_id)
            return None
        
        # Update ID if needed
        metrica_id = metrica_anchor if metrica_anchor else metrica_file_name.replace('.html', '').replace('_1', '')
        
        # Extract definition
        soup = self.get_parsed_file(metrica_file_name)
        definition = extract_metric_definition(soup, metrica_name, metrica_anchor)
        
        # Build file path
        metrica_file_path_with_anchor = f"{metrica_file_name}#{metrica_anchor}" if metrica_anchor else metrica_file_name
        
        # Get tipo
        tipo = definition.get('tipo', 'simples')
        if not tipo:
            tipo = 'simples'
        
        # Create metric object
        metrica = Metrica(
            name=metrica_name,
            id=metrica_id,
            file_path=metrica_file_path_with_anchor,
            dataset_id=dataset_id,
            tipo=tipo,
            applicationObject=ApplicationObjects.METRICA,
            formula=definition.get('formula')
        )
        
        # Extract components based on type
        if metrica.tipo == 'composto':
            extract_composite_metric_components(
                metrica, definition,
                self.get_html_file_path('metrica'),
                dataset_id, visited_ids,
                self.extract  # Pass self.extract for recursion
            )
        else:
            extract_simple_metric_components(
                metrica, definition,
                self.get_html_file_path('funcao'),
                self.get_html_file_path('fato'),
                self.get_html_file_path('tabela_logica'),
                self.base_path,
                self.get_parsed_file
            )
        
        # Cache the metric
        metric_cache[cache_key] = metrica
        
        # Remove from visited set
        if metrica_id:
            visited_ids.discard(metrica_id)
        
        return metrica
    
    def _get_metric_cache_dict(self) -> Dict:
        """Get or create metric cache dict (for backward compatibility)."""
        # Try to get from cache namespace
        cache_dict = self.cache.get('__metric_cache_dict__', namespace='metrics')
        if cache_dict is None:
            cache_dict = {}
            self.cache.set('__metric_cache_dict__', cache_dict, namespace='metrics')
        return cache_dict

