"""Fact parsing utilities with refactored complex functions."""

import re
from pathlib import Path
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from microstrategy_extractor.parsers.base_parser import find_object_section, parse_html_file
from microstrategy_extractor.parsers.link_resolver import LinkResolver
from microstrategy_extractor.utils.text_normalizer import TextNormalizer
from microstrategy_extractor.utils.logger import get_logger
from microstrategy_extractor.core.constants import HTMLClasses, RegexPatterns, TableHeaders
from microstrategy_extractor.core.exceptions import ParsingError, MissingSectionError

logger = get_logger(__name__)


# ============================================================================
# REFACTORED: extract_fact_logic_tables broken into focused sub-functions
# ============================================================================

def _find_expressions_section(anchor_tag: BeautifulSoup) -> Optional[BeautifulSoup]:
    """
    Find the EXPRESSÕES section after an anchor.
    
    Args:
        anchor_tag: Anchor tag to start search from
        
    Returns:
        EXPRESSÕES section table or None
    """
    if not anchor_tag:
        return None
    
    # Start from anchor and look for EXPRESSÕES
    current = anchor_tag.find_next('table', class_=HTMLClasses.SECTIONHEADER)
    attempts = 0
    max_attempts = 20
    
    while current and attempts < max_attempts:
        header_text = current.get_text(strip=True).upper()
        header_norm = TextNormalizer.for_comparison(header_text)
        
        # Check if this is the EXPRESSÕES section
        if TableHeaders.EXPRESSOES.upper() in header_text or 'EXPRESS' in header_norm:
            return current
        
        # Move to next SECTIONHEADER table
        current = current.find_next('table', class_=HTMLClasses.SECTIONHEADER)
        attempts += 1
    
    return None


def _find_data_table(section_table: BeautifulSoup) -> Optional[BeautifulSoup]:
    """
    Find the data table after EXPRESSÕES section header.
    
    Args:
        section_table: EXPRESSÕES section header table
        
    Returns:
        Data table with EXPRESSÃO, MÉTODO, TABELAS FONTE columns or None
    """
    data_table = None
    current = section_table.find_next('table')
    
    # Search for the data table - skip empty tables
    while current:
        rows = current.find_all('tr')
        if rows:
            # Check first row for column headers
            header_row = rows[0]
            header_cells = header_row.find_all(['td', 'th'])
            header_texts = [cell.get_text(strip=True).upper() for cell in header_cells]
            
            # Look for required columns
            has_expressao = False
            has_tabela_fonte = False
            
            for h in header_texts:
                h_norm = TextNormalizer.for_comparison(h)
                
                # Check for EXPRESSÃO
                if TableHeaders.EXPRESSAO.upper() in h or 'EXPRESS' in h_norm:
                    has_expressao = True
                
                # Check for TABELAS FONTE
                if (TableHeaders.TABELAS_FONTE in h or 
                    (TableHeaders.TABELA in h and TableHeaders.FONTE in h)):
                    has_tabela_fonte = True
            
            if has_expressao and has_tabela_fonte:
                return current
        
        # Move to next table
        current = current.find_next('table')
        
        # Stop if we hit another SECTIONHEADER
        if current:
            current_classes = current.get('class', [])
            if HTMLClasses.SECTIONHEADER in str(current_classes):
                break
    
    return None


def _extract_table_references(data_table: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extract logic table references from data table rows.
    
    Args:
        data_table: Data table with columns
        
    Returns:
        List of logic_table dicts with name, id, column_name
    """
    logic_tables = []
    
    # Extract column indices
    header_row = data_table.find('tr')
    if not header_row:
        return []
    
    headers = [th.get_text(strip=True) for th in header_row.find_all(['td', 'th'])]
    expressao_col = None
    table_col = None
    
    # Find column indices with normalization
    for i, h in enumerate(headers):
        h_norm = TextNormalizer.for_comparison(h)
        
        if TableHeaders.EXPRESSAO.upper() in h or 'EXPRESS' in h_norm:
            expressao_col = i
        
        if (TableHeaders.TABELAS_FONTE in h.upper() or 
            (TableHeaders.TABELA in h.upper() and TableHeaders.FONTE in h.upper())):
            table_col = i
    
    if table_col is None:
        return []
    
    # Extract data rows
    for row in data_table.find_all('tr')[1:]:
        cells = row.find_all(['td', 'th'])
        if len(cells) <= table_col:
            continue
        
        # Extract column name from EXPRESSÃO
        column_name = None
        if expressao_col is not None and len(cells) > expressao_col:
            column_name = cells[expressao_col].get_text(strip=True)
        
        # Extract logic_tables from TABELAS FONTE cell
        table_cell = cells[table_col]
        
        for link in table_cell.find_all('a'):
            table_name = link.get_text(strip=True)
            href = link.get('href', '')
            
            if table_name and href:
                match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                if match:
                    table_id = match.group(1)
                    
                    # Check if we already have this table
                    if not any(lt['id'] == table_id for lt in logic_tables):
                        logic_tables.append({
                            'name': table_name,
                            'id': table_id,
                            'file_path': None,
                            'column_name': column_name
                        })
    
    return logic_tables


def extract_fact_logic_tables(soup: BeautifulSoup, fact_name: str, 
                              anchor: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract logic_tables from Fact EXPRESSÕES section.
    
    REFACTORED: Now uses focused sub-functions for better maintainability.
    
    Args:
        soup: BeautifulSoup object
        fact_name: Name of fact object
        anchor: Optional anchor ID
        
    Returns:
        List of logic_table dicts with name, id, file_path, column_name
    """
    # Find anchor if provided
    anchor_tag = None
    if anchor:
        anchor_tag = soup.find('a', {'name': anchor})
        if not anchor_tag:
            return []
    
    # Step 1: Find EXPRESSÕES section
    section_table = _find_expressions_section(anchor_tag)
    if not section_table:
        logger.debug("EXPRESSÕES section not found")
        return []
    
    # Step 2: Find data table
    data_table = _find_data_table(section_table)
    if not data_table:
        logger.debug("Data table not found in EXPRESSÕES section")
        return []
    
    # Step 3: Extract table references
    logic_tables = _extract_table_references(data_table)
    
    return logic_tables


def find_fact_link(fato_index_path: Path, fact_name: Optional[str] = None, 
                  fact_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Find a fact link in Fato.html index.
    
    Uses the generic LinkResolver for consistent behavior.
    
    Args:
        fato_index_path: Path to Fato.html
        fact_name: Optional name of the fact
        fact_id: Optional ID for exact matching
        
    Returns:
        Dict with name, file, anchor, href or None
    """
    if not fato_index_path.exists():
        return None
    
    resolver = LinkResolver(fato_index_path, "Fact")
    return resolver.find_link(object_id=fact_id, object_name=fact_name)


def find_function_link(funcao_index_path: Path, function_id: str) -> Optional[Dict[str, str]]:
    """
    Find a function link in Função.html index by ID.
    
    Uses the generic LinkResolver for consistent behavior.
    
    Args:
        funcao_index_path: Path to Função.html
        function_id: Function ID
        
    Returns:
        Dict with name, file, anchor, href or None
    """
    if not funcao_index_path.exists():
        return None
    
    resolver = LinkResolver(funcao_index_path, "Function")
    return resolver.find_by_id(function_id)


def find_logical_table_link(tabela_logica_index_path: Path, table_name: Optional[str] = None, 
                           table_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Find a logical table link in TabelaLógica.html index.
    
    Uses the generic LinkResolver for consistent behavior.
    
    Args:
        tabela_logica_index_path: Path to TabelaLógica.html
        table_name: Optional name of the table
        table_id: Optional ID for exact matching
        
    Returns:
        Dict with name, file, anchor, href, id or None
    """
    if not tabela_logica_index_path.exists():
        return None
    
    resolver = LinkResolver(tabela_logica_index_path, "LogicalTable")
    return resolver.find_link(object_id=table_id, object_name=table_name)


def extract_expressions_table(soup: BeautifulSoup, object_name: str, 
                             anchor: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract EXPRESSÕES table: expression names and source tables.
    
    Args:
        soup: BeautifulSoup object
        object_name: Name of object
        anchor: Optional anchor ID
        
    Returns:
        List of dicts with 'expressao' and 'tabela_fonte' keys
    """
    section = find_object_section(soup, object_name, anchor)
    if not section:
        return []
    
    expressions = []
    
    # Find EXPRESSÕES section
    for header in section.find_all('td', class_=HTMLClasses.SECTIONHEADER):
        header_text = header.get_text()
        if TableHeaders.EXPRESSOES in header_text or 'EXPRESS' in header_text:
            next_table = header.find_next('table')
            if next_table:
                # Find header row to identify columns
                header_row = next_table.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['td', 'th'])]
                    expr_col = None
                    table_col = None
                    
                    for i, h in enumerate(headers):
                        if TableHeaders.EXPRESSAO in h.upper() or TableHeaders.EXPRESSION in h.upper():
                            expr_col = i
                        if TableHeaders.TABELAS_FONTE in h.upper() or TableHeaders.SOURCE_TABLES in h.upper():
                            table_col = i
                    
                    # Extract data rows
                    for row in next_table.find_all('tr')[1:]:
                        cells = row.find_all(['td', 'th'])
                        if expr_col is not None and table_col is not None and len(cells) > max(expr_col, table_col):
                            expression = cells[expr_col].get_text(strip=True)
                            tabela = cells[table_col].get_text(strip=True)
                            if expression:
                                expressions.append({
                                    'expressao': expression,
                                    'tabela_fonte': tabela
                                })
    
    return expressions

