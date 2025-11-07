"""Helper functions for ReportExtractor - refactored from complex methods."""

from typing import Optional, Set, List, Dict
from pathlib import Path

from models import Metrica, Function, Fact, LogicTable
from html_parser import (
    extract_metric_definition, find_metric_link, find_function_link, 
    find_fact_link, find_logical_table_link, extract_fact_logic_tables
)
from utils.logger import get_logger
from exceptions import CircularReferenceError

logger = get_logger(__name__)


# ============================================================================
# REFACTORED: _extract_metric broken into focused sub-functions
# ============================================================================

def check_circular_reference(metrica_id: Optional[str], metrica_name: str, 
                            visited_ids: Set[str]) -> bool:
    """
    Check if metric would cause circular reference.
    
    Args:
        metrica_id: Metric ID to check
        metrica_name: Metric name for logging
        visited_ids: Set of currently visited metric IDs
        
    Returns:
        True if circular reference detected (should skip), False otherwise
        
    Raises:
        CircularReferenceError: If strict mode enabled
    """
    if metrica_id and metrica_id in visited_ids:
        logger.warning(f"Circular reference detected for metric {metrica_name} (ID: {metrica_id})")
        return True
    return False


def check_metric_cache(cache_key: str, metric_cache: Dict, dataset_id: str, 
                      metrica_id: Optional[str], visited_ids: Set[str]) -> Optional[Metrica]:
    """
    Check cache and return metric copy if found.
    
    Args:
        cache_key: Cache key to check
        metric_cache: Metric cache dictionary
        dataset_id: Dataset ID for new instance
        metrica_id: Metric ID
        visited_ids: Set of visited IDs (for cleanup)
        
    Returns:
        New Metrica instance from cache or None if not cached
    """
    if cache_key in metric_cache:
        # Return a copy to avoid sharing the same instance across datasets
        cached_metric = metric_cache[cache_key]
        
        new_metric = Metrica(
            name=cached_metric.name,
            id=cached_metric.id,
            file_path=cached_metric.file_path,
            dataset_id=dataset_id,  # Use the new dataset_id
            tipo=cached_metric.tipo,
            applicationObject=cached_metric.applicationObject,
            formula=cached_metric.formula,
            function=cached_metric.function,  # Function and Fact can be shared
            fact=cached_metric.fact,
            metricas=cached_metric.metricas.copy() if cached_metric.metricas else []
        )
        
        # Remove from visited set before returning
        if metrica_id:
            visited_ids.discard(metrica_id)
        
        return new_metric
    
    return None


def extract_simple_metric_components(metrica: Metrica, definition: Dict, 
                                    funcao_index_path: Path, fato_index_path: Path,
                                    tabela_logica_index_path: Path, base_path: Path,
                                    get_parsed_file_fn: callable) -> None:
    """
    Extract Function and Fact objects for simple metrics.
    
    Modifies metrica in-place by adding function and fact attributes.
    
    Args:
        metrica: Metrica object to populate
        definition: Metric definition dict from extract_metric_definition
        funcao_index_path: Path to Função.html
        fato_index_path: Path to Fato.html
        tabela_logica_index_path: Path to TabelaLógica.html
        base_path: Base path for HTML files
        get_parsed_file_fn: Function to get parsed HTML file
    """
    function_id = definition.get('function_id')
    fact_id = definition.get('fact_id')
    
    # Find Function object
    if function_id:
        function_link = find_function_link(funcao_index_path, function_id)
        if function_link:
            function_file_path = f"{function_link['file']}#{function_link['anchor']}" if function_link.get('anchor') else function_link['file']
            metrica.function = Function(
                name=function_link['name'],
                file_path=function_file_path
            )
        else:
            logger.warning(f"Function link not found in Função.html: ID {function_id}")
    
    # Find Fact object
    if fact_id:
        fact_link = find_fact_link(fato_index_path, fact_id=fact_id)
        if fact_link:
            fact_file_path = f"{fact_link['file']}#{fact_link['anchor']}" if fact_link.get('anchor') else fact_link['file']
            
            # Extract Fact ID from file_path
            fact_id_from_path = fact_id
            if '#' in fact_file_path:
                fact_id_from_path = fact_file_path.split('#')[1]
            
            # Extract logic_tables from Fact
            fact_logic_tables = _extract_fact_logic_tables_for_metric(
                fact_link, fact_file_path, base_path, 
                tabela_logica_index_path, get_parsed_file_fn
            )
            
            # Create Fact object with logic_tables
            metrica.fact = Fact(
                name=fact_link['name'],
                id=fact_id_from_path,
                file_path=fact_file_path,
                logic_tables=fact_logic_tables
            )
        else:
            logger.warning(f"Fact link not found in Fato.html: ID {fact_id}")


def _extract_fact_logic_tables_for_metric(fact_link: Dict, fact_file_path: str,
                                          base_path: Path, tabela_logica_index_path: Path,
                                          get_parsed_file_fn: callable) -> List[LogicTable]:
    """
    Extract logic tables from a fact for a metric.
    
    Args:
        fact_link: Fact link information
        fact_file_path: Path to fact file
        base_path: Base path for files
        tabela_logica_index_path: Path to TabelaLógica.html
        get_parsed_file_fn: Function to get parsed file
        
    Returns:
        List of LogicTable objects
    """
    fact_file_name = fact_file_path.split('#')[0]
    fact_anchor = fact_file_path.split('#')[1] if '#' in fact_file_path else ''
    
    fact_logic_tables = []
    fact_file = base_path / fact_file_name
    
    if fact_file.exists():
        # Parse the Fact file
        fact_soup = get_parsed_file_fn(fact_file_name)
        
        # Extract logic_tables from EXPRESSÕES section
        logic_tables_data = extract_fact_logic_tables(fact_soup, fact_link['name'], fact_anchor)
        
        logger.debug(f"Extracted {len(logic_tables_data)} logic_tables from Fact {fact_link['name']} (ID: {fact_anchor})")
        
        # Convert to LogicTable objects
        for lt_data in logic_tables_data:
            table_file_path = None
            table_link = find_logical_table_link(
                tabela_logica_index_path,
                table_name=lt_data['name'],
                table_id=lt_data['id']
            )
            if table_link:
                table_file_path = f"{table_link['file']}#{table_link['anchor']}" if table_link.get('anchor') else table_link['file']
            
            logic_table = LogicTable(
                name=lt_data['name'],
                id=lt_data['id'],
                file_path=table_file_path,
                column_name=lt_data.get('column_name')
            )
            fact_logic_tables.append(logic_table)
        
        if not logic_tables_data:
            logger.warning(f"No logic_tables found for Fact {fact_link['name']} (ID: {fact_anchor}) in file {fact_file_name}")
    else:
        logger.warning(f"Fact file not found: {fact_file}")
    
    return fact_logic_tables


def extract_composite_metric_components(metrica: Metrica, definition: Dict,
                                       metrica_index_path: Path, dataset_id: str,
                                       visited_ids: Set[str],
                                       extract_metric_fn: callable) -> None:
    """
    Extract component metrics for composite metrics.
    
    Modifies metrica in-place by adding component metrics.
    
    Args:
        metrica: Metrica object to populate
        definition: Metric definition dict
        metrica_index_path: Path to Métrica.html
        dataset_id: Dataset ID
        visited_ids: Set of visited metric IDs
        extract_metric_fn: Function to recursively extract metrics
    """
    child_metric_ids = definition.get('child_metric_ids', [])
    component_metrics = []
    added_child_ids = set()
    
    for child_metric_id in child_metric_ids:
        # Skip if duplicate
        if child_metric_id in added_child_ids:
            logger.debug(f"Skipping duplicate child metric ID {child_metric_id} in {metrica.name}")
            continue
        
        # Prevent infinite loops
        if child_metric_id in visited_ids:
            logger.warning(f"Skipping child metric {child_metric_id} to prevent circular reference")
            continue
        
        # Find the metric in Métrica.html by ID
        child_metric_link = find_metric_link(metrica_index_path, '', child_metric_id)
        if child_metric_link:
            child_metric_name = child_metric_link['name']
            child_metric_file_path = f"{child_metric_link['file']}#{child_metric_link['anchor']}" if child_metric_link.get('anchor') else child_metric_link['file']
            
            # Recursively extract the child metric
            child_metric = extract_metric_fn(
                child_metric_name, child_metric_file_path, 
                dataset_id, child_metric_id, visited_ids.copy()
            )
            
            if child_metric:
                component_metrics.append(child_metric)
                added_child_ids.add(child_metric_id)
        else:
            logger.warning(f"Child metric not found in Métrica.html: ID {child_metric_id}")
    
    metrica.metricas = component_metrics

