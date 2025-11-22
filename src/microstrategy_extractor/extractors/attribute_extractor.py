"""Attribute extraction logic."""

import hashlib
from pathlib import Path
from typing import Optional, Dict, List

from microstrategy_extractor.extractors.base_extractor import BaseExtractor
from microstrategy_extractor.core.models import Atributo, Formulario, LogicTable
from microstrategy_extractor.parsers.attribute_parser import extract_attribute_forms, find_attribute_link
from microstrategy_extractor.parsers.fact_parser import find_logical_table_link
from microstrategy_extractor.utils.logger import get_logger
from microstrategy_extractor.core.constants import ApplicationSchema

logger = get_logger(__name__)


class AttributeExtractor(BaseExtractor):
    """Extractor for attribute details."""
    
    def extract(self, attr_name_official: str, attr_name_on_dataset: str, 
               attr_file_path: str, dataset_id: str) -> Optional[Atributo]:
        """
        Extract attribute details including expression and source table.
        
        Args:
            attr_name_official: Official name from Atributo.html
            attr_name_on_dataset: Name as found in the dataset
            attr_file_path: File path with anchor
            dataset_id: ID of the dataset this attribute belongs to
            
        Returns:
            Atributo object or None
        """
        # Check cache
        cache_key = f"{dataset_id}:{attr_name_official}"
        cached = self.cache.get(cache_key, namespace="attributes")
        if cached:
            return cached
        
        logger.debug(f"Extracting attribute: {attr_name_official} (on dataset: {attr_name_on_dataset})")
        
        # Extract file name and anchor
        parts = attr_file_path.split('#')
        attr_file_name = parts[0]
        attr_anchor = parts[1] if len(parts) > 1 else ''
        
        attr_file = self.base_path / attr_file_name
        if not attr_file.exists():
            logger.warning(f"Attribute file not found: {attr_file}")
            return None
        
        # Extract attribute ID
        attr_id = attr_anchor if attr_anchor else attr_file_name.replace('.html', '').replace('_1', '')
        
        # Build file path with anchor
        attr_file_path_with_anchor = f"{attr_file_name}#{attr_anchor}" if attr_anchor else attr_file_name
        
        atributo = Atributo(
            name=attr_name_official,
            name_on_dataset=attr_name_on_dataset,
            id=attr_id,
            file_path=attr_file_path_with_anchor,
            dataset_id=dataset_id,
            applicationSchema=ApplicationSchema.ATRIBUTO
        )
        
        # Extract forms
        soup = self.get_parsed_file(attr_file_path)
        forms_data = extract_attribute_forms(soup, attr_name_official, attr_anchor)
        
        # Convert to Formulario objects
        formularios = []
        for form_data in forms_data:
            logic_tables = self._resolve_form_logic_tables(form_data)
            form_name = form_data.get('name', '')
            # Generate deterministic ID from attribute_id + form_name
            form_id = hashlib.md5(f"{attr_id}_{form_name}".encode()).hexdigest().upper()
            formulario = Formulario(
                id=form_id,
                name=form_name,
                logic_tables=logic_tables
            )
            formularios.append(formulario)
        
        atributo.formularios = formularios
        
        # Cache before returning
        self.cache.set(cache_key, atributo, namespace="attributes")
        
        return atributo
    
    def _resolve_form_logic_tables(self, form_data: Dict) -> List[LogicTable]:
        """Resolve file paths for form's logic tables."""
        logic_tables = []
        tabela_logica_index_path = self.get_html_file_path('tabela_logica')
        
        for lt_data in form_data.get('logic_tables', []):
            table_file_path = lt_data.get('file_path')
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
            logic_tables.append(logic_table)
        
        return logic_tables

