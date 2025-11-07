"""Main extraction logic for report data model."""

import re
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Set
import logging

from models import Relatorio, DataSet, Atributo, Metrica, Function, Fact, MetricaRelacao, TabelaFonte, Formulario, LogicTable
from html_parser import (
    parse_html_file, find_object_section, extract_report_links, find_report_by_name, find_report_by_id,
    extract_datasets_from_report, resolve_dataset_link, extract_template_objects, extract_template_objects_report,
    is_report_dataset, extract_graphic_type,
    find_metric_link, find_fact_link, find_function_link, find_attribute_link, extract_metric_definition,
    extract_expressions_table, extract_attribute_forms, find_logical_table_link, extract_fact_logic_tables
)

logger = logging.getLogger(__name__)


class ReportExtractor:
    """Extracts report data model from HTML documentation."""
    
    def __init__(self, base_path: Path):
        """Initialize extractor with base path to HTML files."""
        self.base_path = Path(base_path)
        self.documento_path = self.base_path / "Documento.html"
        self.relatorio_path = self.base_path / "Relatório.html"  # Index for Report-type datasets
        self.cubo_inteligente_path = self.base_path / "CuboInteligente.html"
        self.atalho_path = self.base_path / "Atalho.html"  # Index for Shortcut-type datasets
        self.metrica_index_path = self.base_path / "Métrica.html"
        self.fato_index_path = self.base_path / "Fato.html"
        self.funcao_index_path = self.base_path / "Função.html"
        self.atributo_index_path = self.base_path / "Atributo.html"
        self.tabela_logica_index_path = self.base_path / "TabelaLógica.html"
        
        # Cache for parsed files and resolved links
        self._parsed_files: Dict[str, any] = {}
        self._metric_cache: Dict[str, Metrica] = {}
        self._attribute_cache: Dict[str, Atributo] = {}
    
    def extract_report(self, report_name: str) -> List[Relatorio]:
        """Extract complete data model for all reports with the given name.
        
        Returns a list of Relatorio objects. If multiple reports have the same name,
        all are extracted and returned.
        """
        logger.info(f"Extracting report(s): {report_name}")
        
        # Step 1: Find all reports with this name in Documento.html
        reports_info = find_report_by_name(self.documento_path, report_name)
        if not reports_info:
            logger.warning(f"Report '{report_name}' not found in Documento.html")
            return []
        
        logger.info(f"Found {len(reports_info)} report(s) with name '{report_name}'")
        
        relatorios = []
        
        for report_info in reports_info:
            # Extract report ID from anchor
            report_id = report_info.get('anchor', '')
            if not report_id:
                logger.warning(f"Report anchor not found for: {report_name}")
                continue
            
            report_file = self.base_path / report_info['file']
            if not report_file.exists():
                logger.error(f"Report file not found: {report_file}")
                continue
            
            # File path should include anchor: file.html#anchor
            file_path_with_anchor = f"{report_info['file']}#{report_id}"
            
            logger.info(f"Extracting report ID: {report_id}")
            
            relatorio = Relatorio(
                name=report_info['name'],  # Use the name from HTML to preserve accents
                id=report_id,
                file_path=file_path_with_anchor
            )
            
            # Step 2: Extract datasets
            # Use just the file name (relative to base_path) for _get_parsed_file
            soup = self._get_parsed_file(report_info['file'])
            anchor = report_info.get('anchor', '').split('#')[-1] if '#' in report_info.get('anchor', '') else report_info.get('anchor', '')
            datasets_info = extract_datasets_from_report(soup, report_info['name'], anchor)
            
            logger.info(f"Found {len(datasets_info)} datasets")
            
            for ds_info in datasets_info:
                dataset = self._extract_dataset(ds_info, relatorio.id)
                if dataset:
                    relatorio.datasets.append(dataset)
            
            relatorios.append(relatorio)
        
        return relatorios
    
    def extract_report_by_id(self, report_id: str) -> Optional[Relatorio]:
        """Extract complete data model for a specific report by ID."""
        logger.info(f"Extracting report by ID: {report_id}")
        
        # Step 1: Find report in Documento.html by ID
        report_info = find_report_by_id(self.documento_path, report_id)
        if not report_info:
            logger.warning(f"Report with ID '{report_id}' not found in Documento.html")
            return None
        
        report_file = self.base_path / report_info['file']
        if not report_file.exists():
            logger.error(f"Report file not found: {report_file}")
            return None
        
        # File path should include anchor: file.html#anchor
        file_path_with_anchor = f"{report_info['file']}#{report_id}"
        
        relatorio = Relatorio(
            name=report_info['name'],  # Use the name from Documento.html
            id=report_id,
            file_path=file_path_with_anchor
        )
        
        # Step 2: Extract datasets
        # Use just the file name (relative to base_path) for _get_parsed_file
        soup = self._get_parsed_file(report_info['file'])
        anchor = report_info.get('anchor', '').split('#')[-1] if '#' in report_info.get('anchor', '') else report_info.get('anchor', '')
        datasets_info = extract_datasets_from_report(soup, report_info['name'], anchor)
        
        logger.info(f"Found {len(datasets_info)} datasets")
        
        for ds_info in datasets_info:
            dataset = self._extract_dataset(ds_info, relatorio.id)
            if dataset:
                relatorio.datasets.append(dataset)
        
        return relatorio
    
    def _extract_dataset(self, ds_info: Dict[str, str], relatorio_id: str) -> Optional[DataSet]:
        """Extract dataset details including attributes and metrics."""
        dataset_name = ds_info['name']
        dataset_id = ds_info.get('id', '')
        
        logger.info(f"Extracting dataset: {dataset_name}")
        
        # Resolve dataset file path
        # File path comes from CuboInteligente.html, Relatório.html, or Atalho.html
        # When dataset_id is not available, search by name
        dataset_result = None
        if dataset_id:
            # Search by ID first
            dataset_result = resolve_dataset_link(
                self.base_path, 
                dataset_id, 
                self.cubo_inteligente_path,
                self.relatorio_path,
                self.atalho_path,
                dataset_name=dataset_name
            )
        else:
            # No ID available, try to search by name only
            logger.warning(f"Dataset has no ID (no link in HTML), trying to search by name: {dataset_name}")
            dataset_result = resolve_dataset_link(
                self.base_path, 
                "",  # Empty ID
                self.cubo_inteligente_path,
                self.relatorio_path,
                self.atalho_path,
                dataset_name=dataset_name
            )
        
        # Handle case where dataset is not found in any of the 3 files
        if not dataset_result:
            logger.warning(f"Dataset not found in CuboInteligente.html, Relatório.html, or Atalho.html: {dataset_name} (ID: {dataset_id})")
            # Generate a unique GUID if no ID is available
            if not dataset_id:
                dataset_id = str(uuid.uuid4()).replace('-', '').upper()
                logger.info(f"Generated GUID for dataset without ID: {dataset_id}")
            # Create dataset with blank applicationObject and no attributes/metrics
            dataset = DataSet(
                name=dataset_name,
                id=dataset_id,
                file_path="",  # No file path since dataset was not found
                relatorio_id=relatorio_id,
                applicationObject="",  # Blank applicationObject
                graphic=None
            )
            logger.info(f"Dataset created with blank applicationObject (no attributes/metrics)")
            return dataset
        
        dataset_file, dataset_source = dataset_result
        
        # Extract ID from file path if not already available (when found by name)
        if not dataset_id and '#' in dataset_file:
            dataset_id = dataset_file.split('#')[1]
            logger.info(f"Extracted dataset ID from file path: {dataset_id}")
        
        # Generate a unique GUID if still no ID is available
        if not dataset_id:
            dataset_id = str(uuid.uuid4()).replace('-', '').upper()
            logger.info(f"Generated GUID for dataset without ID: {dataset_id}")
        
        # Handle case where dataset is found in Atalho.html (Shortcut)
        if dataset_source == "Shortcut":
            logger.info(f"Dataset found in Atalho.html (Shortcut type)")
            # Create dataset with Shortcut applicationObject and no attributes/metrics
            dataset = DataSet(
                name=dataset_name,
                id=dataset_id,
                file_path=dataset_file,
                relatorio_id=relatorio_id,
                applicationObject="Shortcut",
                graphic=None
            )
            logger.info(f"Dataset created as Shortcut (no attributes/metrics)")
            return dataset
        
        # Check if file exists (extract just the file name without anchor)
        file_name_only = dataset_file.split('#')[0]
        if not (self.base_path / file_name_only).exists():
            logger.warning(f"Dataset file not found: {file_name_only}")
            return None
        
        # Step 3: Detect dataset type and extract data accordingly
        soup = self._get_parsed_file(dataset_file)
        
        # Check if this is a Report dataset (vs CuboInteligente)
        is_report = is_report_dataset(soup, dataset_id)
        
        if is_report:
            logger.info(f"Dataset is a Report type")
            application_object = "Report"
            graphic_type = extract_graphic_type(soup, dataset_id)
            # Use Report-specific extraction
            atributos_info, metricas_info = extract_template_objects_report(soup, dataset_id)
        else:
            # Set applicationObject based on where it was found
            application_object = "CuboInteligente" if dataset_source == "CuboInteligente" else None
            graphic_type = None
            # Use standard extraction for CuboInteligente
            atributos_info, metricas_info = extract_template_objects(soup, dataset_name, dataset_id)
        
        dataset = DataSet(
            name=dataset_name,
            id=dataset_id,
            file_path=dataset_file,
            relatorio_id=relatorio_id,
            applicationObject=application_object,
            graphic=graphic_type
        )
        
        logger.info(f"Found {len(atributos_info)} attributes and {len(metricas_info)} metrics")
        
        # Extract attributes - get file path from Atributo.html
        for attr_info in atributos_info:
            attr_name_on_dataset = attr_info['name_on_dataset']  # Name as found in dataset
            attr_id = attr_info.get('id')  # ID from HREF [$$$$ID$$$$]
            
            # Find attribute file path in Atributo.html using ID first, then name
            attr_link = find_attribute_link(self.atributo_index_path, attr_name_on_dataset, attr_id)
            if attr_link:
                # Use the official name from Atributo.html (has correct accents)
                attr_name_official = attr_link['name']
                # Build file path with anchor
                attr_file_path = f"{attr_link['file']}#{attr_link['anchor']}" if attr_link.get('anchor') else attr_link['file']
                atributo = self._extract_attribute(
                    attr_name_official,  # Official name from Atributo.html
                    attr_name_on_dataset,  # Name as found in dataset
                    attr_file_path, 
                    dataset.id
                )
            else:
                logger.warning(f"Attribute link not found in Atributo.html: {attr_name_on_dataset} (ID: {attr_id})")
                atributo = None
            
            if atributo:
                dataset.atributos.append(atributo)
        
        # Extract metrics - get file path from Métrica.html
        for metrica_info in metricas_info:
            metrica_name_on_dataset = metrica_info['name_on_dataset']  # Name as found in dataset
            metrica_id = metrica_info.get('id')  # ID from HREF [$$$$ID$$$$]
            
            # Find metric file path in Métrica.html using ID first, then name
            metrica_link = find_metric_link(self.metrica_index_path, metrica_name_on_dataset, metrica_id)
            if metrica_link:
                # Use the official name from Métrica.html (has correct accents)
                metrica_name_official = metrica_link['name']
                # Build file path with anchor
                metrica_file_path = f"{metrica_link['file']}#{metrica_link['anchor']}" if metrica_link.get('anchor') else metrica_link['file']
                # Use metric ID in cache key to ensure uniqueness
                metrica_anchor = metrica_link.get('anchor', metrica_id) if metrica_link.get('anchor') else metrica_id
                metrica = self._extract_metric(metrica_name_official, metrica_file_path, dataset.id, metrica_anchor)
            else:
                logger.warning(f"Metric link not found in Métrica.html: {metrica_name_on_dataset} (ID: {metrica_id})")
                metrica = None
            
            if metrica:
                dataset.metricas.append(metrica)
        
        return dataset
    
    def _extract_attribute(self, attr_name_official: str, attr_name_on_dataset: str, attr_file_path: str, dataset_id: str) -> Optional[Atributo]:
        """Extract attribute details including expression and source table.
        
        Args:
            attr_name_official: Official name from Atributo.html (with correct accents)
            attr_name_on_dataset: Name as found in the dataset
            attr_file_path: File path with anchor (e.g., "file.html#anchor")
            dataset_id: ID of the dataset this attribute belongs to
        """
        # Check cache
        cache_key = f"{dataset_id}:{attr_name_official}"
        if cache_key in self._attribute_cache:
            return self._attribute_cache[cache_key]
        
        logger.debug(f"Extracting attribute: {attr_name_official} (on dataset: {attr_name_on_dataset})")
        
        # Extract file name and anchor from file_path
        parts = attr_file_path.split('#')
        attr_file_name = parts[0]
        attr_anchor = parts[1] if len(parts) > 1 else ''
        
        attr_file = self.base_path / attr_file_name
        if not attr_file.exists():
            logger.warning(f"Attribute file not found: {attr_file}")
            return None
        
        # Extract attribute ID from anchor
        attr_id = attr_anchor if attr_anchor else ''
        if not attr_id:
            # Fallback: try to extract from file name
            attr_id = attr_file_name.replace('.html', '').replace('_1', '')
        
        # Build file path with anchor
        attr_file_path_with_anchor = f"{attr_file_name}#{attr_anchor}" if attr_anchor else attr_file_name
        
        atributo = Atributo(
            name=attr_name_official,  # Official name from Atributo.html
            name_on_dataset=attr_name_on_dataset,  # Name as found in dataset
            id=attr_id,
            file_path=attr_file_path_with_anchor,
            dataset_id=dataset_id,
            applicationSchema="Atributo"  # Found in Atributo.html
        )
        
        # Extract forms and their source tables from DETALHES DOS FORMULÁRIOS DE ATRIBUTO
        soup = self._get_parsed_file(attr_file_path)
        forms_data = extract_attribute_forms(soup, attr_name_official, attr_anchor)
        
        # Convert forms data to Formulario objects
        formularios = []
        for form_data in forms_data:
            # Convert logic_tables to LogicTable objects
            logic_tables = []
            for lt_data in form_data.get('logic_tables', []):
                # Resolve file_path from TabelaLógica.html using the table ID
                table_file_path = lt_data.get('file_path')
                table_link = find_logical_table_link(
                    self.tabela_logica_index_path,
                    table_name=lt_data['name'],
                    table_id=lt_data['id']
                )
                if table_link:
                    # Build file path with anchor
                    table_file_path = f"{table_link['file']}#{table_link['anchor']}" if table_link.get('anchor') else table_link['file']
                
                logic_table = LogicTable(
                    name=lt_data['name'],
                    id=lt_data['id'],
                    file_path=table_file_path,
                    column_name=lt_data.get('column_name')  # Note: attribute forms don't have column_name
                )
                logic_tables.append(logic_table)
            
            formulario = Formulario(
                name=form_data.get('name', ''),
                logic_tables=logic_tables
            )
            formularios.append(formulario)
        
        atributo.formularios = formularios
        
        self._attribute_cache[cache_key] = atributo
        return atributo
    
    def _extract_metric(self, metrica_name: str, metrica_file_path: str, dataset_id: str, metrica_id: Optional[str] = None, visited_ids: Optional[Set[str]] = None) -> Optional[Metrica]:
        """Extract metric details, handling both simple and composite metrics.
        
        Args:
            metrica_name: Name of the metric
            metrica_file_path: File path with anchor (e.g., "file.html#anchor")
            dataset_id: ID of the dataset this metric belongs to
            metrica_id: Optional metric ID for cache key uniqueness
            visited_ids: Set of metric IDs already being processed (to prevent infinite loops)
        """
        # Initialize visited_ids if not provided (to track recursion depth)
        if visited_ids is None:
            visited_ids = set()
        
        # Extract metric ID from file_path if not provided
        if not metrica_id:
            parts = metrica_file_path.split('#')
            metrica_id = parts[1] if len(parts) > 1 else ''
        
        # Prevent infinite loops: if we're already processing this metric, return None
        if metrica_id and metrica_id in visited_ids:
            logger.warning(f"Circular reference detected for metric {metrica_name} (ID: {metrica_id}). Skipping to prevent infinite loop.")
            return None
        
        # Add this metric ID to visited set
        if metrica_id:
            visited_ids.add(metrica_id)
        
        # Check cache - use metric ID to ensure uniqueness
        cache_key = f"{metrica_id}:{metrica_name}" if metrica_id else f"{dataset_id}:{metrica_name}"
        if cache_key in self._metric_cache:
            # Return a copy to avoid sharing the same instance across datasets
            cached_metric = self._metric_cache[cache_key]
            # Create a new instance with the same data but different dataset_id
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
        
        logger.debug(f"Extracting metric: {metrica_name}")
        
        # Extract file name and anchor from file_path
        parts = metrica_file_path.split('#')
        metrica_file_name = parts[0]
        metrica_anchor = parts[1] if len(parts) > 1 else ''
        
        metrica_file = self.base_path / metrica_file_name
        if not metrica_file.exists():
            logger.warning(f"Metric file not found: {metrica_file}")
            return None
        
        # Extract metric ID from anchor
        metrica_id = metrica_anchor if metrica_anchor else ''
        if not metrica_id:
            # Fallback: try to extract from file name
            metrica_id = metrica_file_name.replace('.html', '').replace('_1', '')
        
        # Extract metric definition
        soup = self._get_parsed_file(metrica_file_name)
        definition = extract_metric_definition(soup, metrica_name, metrica_anchor)
        
        # Build file path with anchor
        metrica_file_path_with_anchor = f"{metrica_file_name}#{metrica_anchor}" if metrica_anchor else metrica_file_name
        
        # Get tipo from definition, default to 'simples' if not found
        tipo = definition.get('tipo', 'simples')
        if not tipo:
            tipo = 'simples'
        
        metrica = Metrica(
            name=metrica_name,
            id=metrica_id,
            file_path=metrica_file_path_with_anchor,
            dataset_id=dataset_id,
            tipo=tipo,  # 'simples' or 'composto' from "Tipo de métrica" field
            applicationObject="Metrica",  # Found in Métrica.html
            formula=definition.get('formula')
        )
        
        # Step 4: Handle metric type
        if metrica.tipo == 'composto':
            # Extract component metrics from child_metric_ids
            child_metric_ids = definition.get('child_metric_ids', [])
            component_metrics = []
            
            # Track child metric IDs we've already added to prevent duplicates
            added_child_ids = set()
            
            for child_metric_id in child_metric_ids:
                # Skip if we've already added this child metric (duplicate in child_metric_ids list)
                if child_metric_id in added_child_ids:
                    logger.debug(f"Skipping duplicate child metric ID {child_metric_id} in {metrica_name}")
                    continue
                
                # Prevent infinite loops: check if we're already processing this child
                if child_metric_id in visited_ids:
                    logger.warning(f"Skipping child metric {child_metric_id} to prevent circular reference")
                    continue
                
                # Find the metric in Métrica.html by ID
                child_metric_link = find_metric_link(self.metrica_index_path, '', child_metric_id)
                if child_metric_link:
                    child_metric_name = child_metric_link['name']
                    child_metric_file_path = f"{child_metric_link['file']}#{child_metric_link['anchor']}" if child_metric_link.get('anchor') else child_metric_link['file']
                    # Recursively extract the child metric (pass visited_ids to prevent loops)
                    child_metric = self._extract_metric(child_metric_name, child_metric_file_path, dataset_id, child_metric_id, visited_ids.copy())
                    if child_metric:
                        component_metrics.append(child_metric)
                        added_child_ids.add(child_metric_id)
                else:
                    logger.warning(f"Child metric not found in Métrica.html: ID {child_metric_id}")
            
            metrica.metricas = component_metrics
        else:
            # Simple metric: find Function and Fact objects
            function_id = definition.get('function_id')
            fact_id = definition.get('fact_id')
            
            # Find Function object
            if function_id:
                function_link = find_function_link(self.funcao_index_path, function_id)
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
                fact_link = find_fact_link(self.fato_index_path, fact_id=fact_id)
                if fact_link:
                    fact_file_path = f"{fact_link['file']}#{fact_link['anchor']}" if fact_link.get('anchor') else fact_link['file']
                    
                    # Extract Fact ID from file_path (the part after #)
                    fact_id_from_path = fact_id
                    if '#' in fact_file_path:
                        fact_id_from_path = fact_file_path.split('#')[1]
                    
                    # Extract logic_tables from Fact EXPRESSÕES section first
                    # Access the Fact file and find the object by ID
                    fact_file_name = fact_file_path.split('#')[0]
                    fact_anchor = fact_file_path.split('#')[1] if '#' in fact_file_path else ''
                    
                    fact_logic_tables = []
                    fact_file = self.base_path / fact_file_name
                    if fact_file.exists():
                        # Parse the Fact file
                        fact_soup = self._get_parsed_file(fact_file_name)
                        # Extract logic_tables from EXPRESSÕES section
                        logic_tables_data = extract_fact_logic_tables(fact_soup, fact_link['name'], fact_anchor)
                        
                        logger.debug(f"Extracted {len(logic_tables_data)} logic_tables from Fact {fact_link['name']} (ID: {fact_anchor})")
                        
                        # Convert to LogicTable objects and resolve file_path from TabelaLógica.html
                        for lt_data in logic_tables_data:
                            # Resolve file_path from TabelaLógica.html using the table ID
                            table_file_path = None
                            table_link = find_logical_table_link(
                                self.tabela_logica_index_path,
                                table_name=lt_data['name'],
                                table_id=lt_data['id']
                            )
                            if table_link:
                                # Build file path with anchor
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
                    
                    # Create Fact object with logic_tables
                    metrica.fact = Fact(
                        name=fact_link['name'],
                        id=fact_id_from_path,
                        file_path=fact_file_path,
                        logic_tables=fact_logic_tables
                    )
                else:
                    logger.warning(f"Fact link not found in Fato.html: ID {fact_id}")
        
        # Cache the metric before returning
        self._metric_cache[cache_key] = metrica
        
        # Remove from visited set before returning (after processing is complete)
        if metrica_id:
            visited_ids.discard(metrica_id)
        
        return metrica
    
    def _extract_component_metrics(self, formula: str, dataset_id: str) -> List[Metrica]:
        """Extract component metrics from composite metric formula."""
        if not formula:
            return []
        
        # Extract metric names from formula (simple heuristic)
        # Look for patterns like "Vl. Ressarcimento" or similar
        # This is a simplified approach - may need refinement
        component_names = []
        
        # Try to find metric names in the formula
        # Common patterns: metric names are usually capitalized or have specific formats
        words = re.findall(r'[A-Z][a-zA-Z0-9.\s]+', formula)
        for word in words:
            word = word.strip()
            if len(word) > 3 and not word in ['Sum', 'Avg', 'Max', 'Min', 'Count']:
                # Check if it's a metric by looking it up (if index exists)
                if self.metrica_index_path.exists():
                    metrica_link = find_metric_link(self.metrica_index_path, word)
                    if metrica_link:
                        component_names.append(word)
        
        component_metrics = []
        for comp_name in component_names:
            comp_metric = self._extract_metric(comp_name, dataset_id, '')
            if comp_metric:
                component_metrics.append(comp_metric)
        
        return component_metrics
    
    def _extract_fato_from_formula(self, formula: str) -> Optional[str]:
        """Extract Fato name from metric formula (e.g., 'Sum ( VL_RESS )' -> 'VL_RESS')."""
        if not formula:
            return None
        
        # Look for patterns like Sum( FACT_NAME ) or similar
        match = re.search(r'Sum\s*\(\s*([A-Z_]+)\s*\)', formula, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try other aggregation functions
        for func in ['Avg', 'Max', 'Min', 'Count']:
            match = re.search(rf'{func}\s*\(\s*([A-Z_]+)\s*\)', formula, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_metric_source_table(self, fato_name: str) -> Optional[str]:
        """Extract source table for a metric via Fato."""
        # Find Fato link (if index exists)
        fato_link = None
        if self.fato_index_path.exists():
            fato_link = find_fact_link(self.fato_index_path, fato_name)
        if not fato_link:
            logger.warning(f"Fact link not found: {fato_name}")
            return None
        
        fato_file = self.base_path / fato_link['file']
        if not fato_file.exists():
            logger.warning(f"Fact file not found: {fato_file}")
            return None
        
        # Extract EXPRESSÕES table
        soup = self._get_parsed_file(str(fato_file))
        fato_anchor = fato_link.get('anchor', '').split('#')[-1] if '#' in fato_link.get('anchor', '') else fato_link.get('anchor', '')
        expressions = extract_expressions_table(soup, fato_name, fato_anchor)
        
        if expressions:
            # Find expression matching the fato name
            for expr in expressions:
                if expr['expressao'] == fato_name:
                    tabela_fonte = expr.get('tabela_fonte')
                    if tabela_fonte:
                        return tabela_fonte
        
        return None
    
    def _get_parsed_file(self, file_path: str) -> any:
        """Get parsed HTML file, using cache if available.
        
        file_path can be either:
        - Just the file name: "file.html"
        - File with anchor: "file.html#anchor"
        - Full path: "path/file.html#anchor"
        """
        # Extract just the file path without anchor for file system operations
        file_path_only = file_path.split('#')[0]
        
        # Build full path - if it's already absolute, use it; otherwise make it relative to base_path
        if Path(file_path_only).is_absolute():
            full_path = Path(file_path_only)
        else:
            full_path = self.base_path / file_path_only
        
        full_path_str = str(full_path)
        if full_path_str not in self._parsed_files:
            self._parsed_files[full_path_str] = parse_html_file(full_path)
        return self._parsed_files[full_path_str]
    
    def extract_all_reports(self) -> List[Relatorio]:
        """Extract data model for all reports in Documento.html."""
        reports_info = extract_report_links(self.documento_path)
        relatorios = []
        
        logger.info(f"Found {len(reports_info)} reports to process")
        
        for report_info in reports_info:
            try:
                # extract_report returns a list of reports (can be multiple with same name)
                extracted_reports = self.extract_report(report_info['name'])
                if extracted_reports:
                    relatorios.extend(extracted_reports)
            except Exception as e:
                logger.error(f"Error extracting report '{report_info['name']}': {e}")
                continue
        
        return relatorios

