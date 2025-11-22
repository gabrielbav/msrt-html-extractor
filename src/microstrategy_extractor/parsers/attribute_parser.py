"""Attribute parsing utilities."""

import re
from pathlib import Path
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from microstrategy_extractor.parsers.base_parser import parse_html_file
from microstrategy_extractor.parsers.link_resolver import LinkResolver
from microstrategy_extractor.utils.text_normalizer import TextNormalizer
from microstrategy_extractor.utils.logger import get_logger
from microstrategy_extractor.core.constants import HTMLClasses, RegexPatterns, TableHeaders
from microstrategy_extractor.core.exceptions import ParsingError

logger = get_logger(__name__)


def extract_attribute_forms(soup: BeautifulSoup, object_name: str, 
                           anchor: Optional[str] = None) -> List[Dict[str, any]]:
    """
    Extract DETALHES DOS FORMULÁRIOS DE ATRIBUTO table.
    
    Returns a list of forms, where each form contains:
    - name: Form name (e.g., "ID", "Codigo Agência")
    - logic_tables: List of dicts with name, id, file_path, column_name
    
    Args:
        soup: BeautifulSoup object
        object_name: Name of attribute object
        anchor: Optional anchor ID
        
    Returns:
        List of form dicts
    """
    # Find anchor if provided
    anchor_tag = None
    if anchor:
        anchor_tag = soup.find('a', {'name': anchor})
        if not anchor_tag:
            return []
    
    forms = []
    
    # Find all attribute anchors (32 hex chars, no underscore)
    all_attr_anchors = []
    for a in soup.find_all('a', {'name': True}):
        name = a.get('name', '')
        if len(name) == 32 and '_' not in name and re.match(RegexPatterns.HEX_32_CHARS, name):
            all_attr_anchors.append(a)
    
    # Find current and next attribute anchor
    next_anchor = None
    if anchor_tag:
        try:
            current_idx = all_attr_anchors.index(anchor_tag)
            if current_idx + 1 < len(all_attr_anchors):
                next_anchor = all_attr_anchors[current_idx + 1]
        except ValueError:
            pass
    
    # Find DETALHES DOS FORMULÁRIOS section
    section_table = None
    if anchor_tag:
        current = anchor_tag.find_next('table', class_=HTMLClasses.SECTIONHEADER)
        attempts = 0
        max_attempts = 20
        
        while current and attempts < max_attempts:
            # Stop if we hit next attribute
            if next_anchor:
                try:
                    if list(soup.descendants).index(current) >= list(soup.descendants).index(next_anchor):
                        break
                except ValueError:
                    pass
            
            header_text = current.get_text(strip=True).upper()
            if 'DETALHES' in header_text and ('FORMULÁRIO' in header_text or 'FORMULARIO' in header_text):
                section_table = current
                break
            current = current.find_next('table', class_=HTMLClasses.SECTIONHEADER)
            attempts += 1
    
    if not section_table:
        return []
    
    # Find all form anchors (have underscore) after section_table
    form_anchors_to_process = []
    current = section_table.find_next('a')
    while current:
        if next_anchor and current == next_anchor:
            break
        
        anchor_name = current.get('name', '')
        if anchor_name and '_' in anchor_name:
            form_anchors_to_process.append(current)
        
        current = current.find_next('a')
        
        # Safety: stop after next attribute anchor
        if next_anchor:
            try:
                curr_idx = list(soup.descendants).index(current) if current else float('inf')
                next_idx = list(soup.descendants).index(next_anchor)
                if curr_idx >= next_idx:
                    break
            except (ValueError, TypeError):
                pass
    
    # Process each form anchor
    for form_anchor in form_anchors_to_process:
        if not form_anchor:
            continue
        
        form = _extract_single_form(form_anchor, soup)
        if form:
            forms.append(form)
    
    return forms


def _extract_single_form(form_anchor: BeautifulSoup, soup: BeautifulSoup) -> Optional[Dict]:
    """
    Extract data for a single attribute form.
    
    Args:
        form_anchor: Anchor tag for the form
        soup: Full BeautifulSoup object
        
    Returns:
        Form dict with name and logic_tables
    """
    # Get form name from table after anchor
    form_name_table = form_anchor.find_next('table')
    if not form_name_table:
        return None
    
    # Extract form name
    form_name = None
    form_name_rows = form_name_table.find_all('tr')
    if form_name_rows:
        form_name_cell = form_name_rows[0].find('td')
        if form_name_cell:
            bold_tag = form_name_cell.find('b')
            if bold_tag:
                form_name = bold_tag.get_text(strip=True)
            else:
                form_name = form_name_cell.get_text(strip=True)
    
    if not form_name:
        return None
    
    # Find PROPRIEDADE/VALORES table
    prop_table = form_name_table.find_next('table')
    if not prop_table:
        return None
    
    # Find nested table with EXPRESSÃO header
    nested_table = _find_nested_expressions_table(prop_table)
    
    if not nested_table:
        return None
    
    # Extract logic tables from nested table
    logic_tables = _extract_logic_tables_from_form(nested_table)
    
    return {
        'name': form_name,
        'logic_tables': logic_tables
    }


def _find_nested_expressions_table(prop_table: BeautifulSoup) -> Optional[BeautifulSoup]:
    """
    Find nested table with EXPRESSÃO header inside VALORES cell.
    
    Args:
        prop_table: Properties table
        
    Returns:
        Nested table or None
    """
    for cell in prop_table.find_all('td'):
        nested = cell.find('table')
        if nested:
            nested_rows = nested.find_all('tr')
            if nested_rows:
                nested_headers = [th.get_text(strip=True) for th in nested_rows[0].find_all(['td', 'th'])]
                header_text = ' '.join(nested_headers).upper()
                if TableHeaders.EXPRESSAO in header_text or TableHeaders.EXPRESSION in header_text:
                    return nested
    
    return None


def _extract_logic_tables_from_form(nested_table: BeautifulSoup) -> List[Dict]:
    """
    Extract logic tables from form's nested table.
    
    Args:
        nested_table: Nested table with EXPRESSÃO, MÉTODO, TABELAS FONTE columns
        
    Returns:
        List of logic_table dicts
    """
    logic_tables = []
    
    nested_rows = nested_table.find_all('tr')
    if not nested_rows:
        return logic_tables
    
    # Find columns
    header_row = nested_rows[0]
    headers = [th.get_text(strip=True) for th in header_row.find_all(['td', 'th'])]
    expr_col = None
    table_col = None
    
    # Find column indices
    for i, h in enumerate(headers):
        h_norm = TextNormalizer.for_comparison(h)
        # Normalize the constants too for proper comparison
        expressao_norm = TextNormalizer.for_comparison(TableHeaders.EXPRESSAO)
        expression_norm = TextNormalizer.for_comparison(TableHeaders.EXPRESSION)
        if expressao_norm in h_norm or expression_norm in h_norm:
            expr_col = i
        if TableHeaders.TABELAS_FONTE in h.upper() or (TableHeaders.TABELA in h.upper() and TableHeaders.FONTE in h.upper()):
            table_col = i
    
    # Extract data rows
    for row in nested_rows[1:]:
        cells = row.find_all(['td', 'th'])
        
        # Extract column name from EXPRESSÃO
        column_name = None
        if expr_col is not None and len(cells) > expr_col:
            column_name = cells[expr_col].get_text(strip=True)
            # Only set to None if empty string
            if not column_name:
                column_name = None
        
        # Extract source tables
        if table_col is not None and len(cells) > table_col:
            table_cell = cells[table_col]
            for link in table_cell.find_all('a'):
                table_name = link.get_text(strip=True)
                href = link.get('href', '')
                if table_name and href:
                    match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                    if match:
                        table_id = match.group(1)
                        logic_tables.append({
                            'name': table_name,
                            'id': table_id,
                            'file_path': None,
                            'column_name': column_name
                        })
    
    return logic_tables


def find_attribute_link(atributo_index_path: Path, attribute_name: str, 
                       attribute_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Find an attribute link in Atributo.html index.
    
    Uses the generic LinkResolver for consistent behavior.
    
    Args:
        atributo_index_path: Path to Atributo.html
        attribute_name: Name of the attribute
        attribute_id: Optional ID for exact matching
        
    Returns:
        Dict with name, file, anchor, href or None
    """
    if not atributo_index_path.exists():
        return None
    
    resolver = LinkResolver(atributo_index_path, "Attribute")
    return resolver.find_link(object_id=attribute_id, object_name=attribute_name)

