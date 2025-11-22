"""Metric parsing utilities with refactored complex functions."""

import re
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from pathlib import Path

from microstrategy_extractor.parsers.base_parser import find_object_section, parse_html_file
from microstrategy_extractor.parsers.link_resolver import LinkResolver
from microstrategy_extractor.utils.text_normalizer import TextNormalizer, normalize_for_comparison
from microstrategy_extractor.utils.logger import get_logger
from microstrategy_extractor.core.constants import HTMLSections, HTMLClasses, RegexPatterns, HTMLImages, TableHeaders
from microstrategy_extractor.core.exceptions import ParsingError

logger = get_logger(__name__)


# ============================================================================
# REFACTORED: extract_metric_definition broken into focused sub-functions
# ============================================================================

def _find_definition_section(soup: BeautifulSoup, object_name: str, 
                             anchor: Optional[str] = None) -> Optional[BeautifulSoup]:
    """
    Find the DEFINIÇÃO section for a metric.
    
    Args:
        soup: BeautifulSoup object
        object_name: Name of metric object
        anchor: Optional anchor ID
        
    Returns:
        DEFINIÇÃO section table or None
    """
    # First, try to find the object section
    section = find_object_section(soup, object_name, anchor)
    search_area = section if section else soup
    logger.debug(f"_find_definition_section: search_area={'object_section' if section else 'full_soup'}")
    
    # If anchor is provided, find the anchor first
    anchor_tag = None
    if anchor:
        anchor_tag = search_area.find('a', {'name': anchor})
        if not anchor_tag:
            anchor_tag = soup.find('a', {'name': anchor})
        logger.debug(f"Anchor tag found: {anchor_tag is not None}")
    
    # Find all DEFINIÇÃO sections
    def_sections = []
    for table in search_area.find_all('table', class_=HTMLClasses.SECTIONHEADER):
        header_text = table.get_text(strip=True)
        # Normalize for comparison (remove accents)
        header_text_norm = normalize_for_comparison(header_text)
        if HTMLSections.DEFINICAO_NORM in header_text_norm:
            def_sections.append(table)
            logger.debug(f"Found DEFINIÇÃO section in search_area: {header_text[:50]}")
    
    # If no sections found in search_area, search entire document
    if not def_sections:
        logger.debug("No DEFINIÇÃO in search_area, searching full document")
        for table in soup.find_all('table', class_=HTMLClasses.SECTIONHEADER):
            header_text = table.get_text(strip=True)
            # Normalize for comparison (remove accents)
            header_text_norm = normalize_for_comparison(header_text)
            if HTMLSections.DEFINICAO_NORM in header_text_norm:
                def_sections.append(table)
                logger.debug(f"Found DEFINIÇÃO section in full soup: {header_text[:50]}")
    
    logger.debug(f"Total DEFINIÇÃO sections found: {len(def_sections)}")
    
    # If we have an anchor, find the DEFINIÇÃO section that comes after it
    if anchor_tag and def_sections:
        logger.debug("Searching for DEFINIÇÃO after anchor")
        # Find the first DEFINIÇÃO after the anchor in document order
        for elem in soup.descendants:
            if elem == anchor_tag:
                # Found anchor, look for next DEFINIÇÃO
                current = anchor_tag
                while current:
                    current = current.find_next()
                    if current and current.name == 'table' and HTMLClasses.SECTIONHEADER in str(current.get('class', [])):
                        header_text = current.get_text(strip=True)
                        header_text_norm = normalize_for_comparison(header_text)
                        if HTMLSections.DEFINICAO_NORM in header_text_norm:
                            logger.debug(f"Returning DEFINIÇÃO after anchor")
                            return current
                break
    
    # If no target found yet, use the first DEFINIÇÃO
    if def_sections:
        logger.debug(f"Returning first DEFINIÇÃO section")
        return def_sections[0]
    
    logger.warning(f"No DEFINIÇÃO section found for '{object_name}'")
    return None


def _extract_metric_type_from_section(target_section: BeautifulSoup) -> Optional[str]:
    """
    Extract metric type (simples/composto) from DEFINIÇÃO section.
    
    Args:
        target_section: DEFINIÇÃO section table
        
    Returns:
        'simples', 'composto', or None
    """
    current = target_section.find_next('table')
    while current:
        rows = current.find_all('tr')
        if rows:
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    # Look for "Tipo de métrica"
                    label_upper = label.upper()
                    if 'TIPO' in label_upper and ('MÉTRICA' in label_upper or 'METRICA' in label_upper):
                        value_lower = value.lower()
                        if 'composto' in value_lower or 'composite' in value_lower:
                            return 'composto'
                        else:
                            return 'simples'
            
            # If we found tipo, stop
            if any('TIPO' in cell.get_text(strip=True).upper() for cell in rows[0].find_all(['td', 'th'])):
                break
        
        # Find next table, but stop if we hit another SECTIONHEADER
        next_elem = current.find_next()
        if next_elem and next_elem.name == 'table' and HTMLClasses.SECTIONHEADER in str(next_elem.get('class', [])):
            break
        current = current.find_next('table')
    
    return None


def _extract_formula_components(target_section: BeautifulSoup) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract formula, function_id, and fact_id from DEFINIÇÃO section.
    
    Args:
        target_section: DEFINIÇÃO section table
        
    Returns:
        Tuple of (formula, function_id, fact_id)
    """
    formula = None
    function_id = None
    fact_id = None
    
    current = target_section.find_next('table')
    while current:
        rows = current.find_all('tr')
        if rows:
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    label_upper = label.upper()
                    
                    # Look for Fórmula
                    if TableHeaders.FORMULA in label_upper or 'FORMULA' in label_upper:
                        formula_cell = cells[1]
                        
                        # Extract formula text carefully
                        formula_parts = []
                        seen_elements = set()
                        last_img = None
                        
                        for elem in formula_cell.descendants:
                            if isinstance(elem, str):
                                text = elem.strip()
                                if text and text not in seen_elements:
                                    if text in ['(', ')']:
                                        formula_parts.append(text)
                                    elif text not in [' ', '']:
                                        formula_parts.append(text)
                                        seen_elements.add(text)
                            elif hasattr(elem, 'name'):
                                if elem.name == 'img':
                                    last_img = elem
                                elif elem.name == 'a':
                                    link_text = elem.get_text(strip=True)
                                    if link_text and link_text not in seen_elements:
                                        formula_parts.append(link_text)
                                        seen_elements.add(link_text)
                                    
                                    # Extract ID from HREF
                                    href = elem.get('href', '')
                                    if href:
                                        match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                                        if match:
                                            extracted_id = match.group(1)
                                            if last_img:
                                                img_src = last_img.get('src', '').lower()
                                                if 'function' in img_src:
                                                    if function_id is None:
                                                        function_id = extracted_id
                                                elif 'fact' in img_src:
                                                    if fact_id is None:
                                                        fact_id = extracted_id
                                            else:
                                                # Fallback: first is function, second is fact
                                                if function_id is None:
                                                    function_id = extracted_id
                                                elif fact_id is None:
                                                    fact_id = extracted_id
                        
                        # Clean up formula
                        if formula_parts:
                            # Remove consecutive duplicates
                            cleaned_parts = []
                            prev = None
                            for part in formula_parts:
                                if part != prev or part in ['(', ')', '/', '+', '-', '*']:
                                    cleaned_parts.append(part)
                                prev = part
                            formula = ' '.join(cleaned_parts)
                            formula = re.sub(r'\s+', ' ', formula).strip()
                            formula = re.sub(r'\s*\(\s*', ' (', formula)
                            formula = re.sub(r'\s*\)\s*', ')', formula)
        
        # Find next table
        next_elem = current.find_next()
        if next_elem and next_elem.name == 'table' and HTMLClasses.SECTIONHEADER in str(next_elem.get('class', [])):
            break
        current = current.find_next('table')
    
    return formula, function_id, fact_id


def _extract_child_metric_ids(target_section: BeautifulSoup, anchor: Optional[str], 
                              soup: BeautifulSoup) -> List[str]:
    """
    Extract child metric IDs for composite metrics.
    
    Args:
        target_section: DEFINIÇÃO section table
        anchor: Metric anchor ID
        soup: Full BeautifulSoup object
        
    Returns:
        List of child metric IDs
    """
    child_metric_ids = []
    
    # Look for child metrics ONLY in the formula section
    formula_processed = False
    current = target_section.find_next('table')
    
    while current and not formula_processed:
        rows = current.find_all('tr')
        if rows:
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    if TableHeaders.FORMULA in label.upper() or 'FORMULA' in label.upper():
                        formula_cell = cells[1]
                        
                        # Look for links with Metric.bmp
                        for link in formula_cell.find_all('a'):
                            href = link.get('href', '')
                            if href and '[$$$$' in href:
                                # Find the previous image sibling
                                prev_img = None
                                prev = link.previous_sibling
                                while prev:
                                    if hasattr(prev, 'name') and prev.name == 'img':
                                        prev_img = prev
                                        break
                                    prev = prev.previous_sibling
                                
                                # Check if this is a metric link
                                if prev_img:
                                    img_src = prev_img.get('src', '').lower()
                                    if HTMLImages.METRIC.lower() in img_src:
                                        match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                                        if match:
                                            metric_id = match.group(1)
                                            if metric_id not in child_metric_ids:
                                                child_metric_ids.append(metric_id)
                        
                        formula_processed = True
                        break
        
        if not formula_processed:
            current = current.find_next('table')
            if current:
                next_elem = current.find_next()
                if next_elem and next_elem.name == 'table' and HTMLClasses.SECTIONHEADER in str(next_elem.get('class', [])):
                    break
        else:
            break
    
    return child_metric_ids


def extract_metric_definition(soup: BeautifulSoup, object_name: str, 
                              anchor: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Extract metric definition: tipo, formula, function_id, and fact_id.
    
    REFACTORED: Now uses focused sub-functions for better maintainability.
    
    Args:
        soup: BeautifulSoup object
        object_name: Name of metric object
        anchor: Optional anchor ID
        
    Returns:
        Dict with 'tipo', 'formula', 'function_id', 'fact_id', 'child_metric_ids'
    """
    # Find DEFINIÇÃO section
    logger.debug(f"extract_metric_definition: object_name={object_name}, anchor={anchor}")
    target_section = _find_definition_section(soup, object_name, anchor)
    
    if not target_section:
        logger.warning(f"DEFINIÇÃO section not found for metric '{object_name}' (anchor={anchor})")
        return {
            'tipo': 'simples',
            'formula': None,
            'function_id': None,
            'fact_id': None,
            'child_metric_ids': []
        }
    
    logger.debug(f"Found DEFINIÇÃO section for '{object_name}'")
    
    # Extract type
    tipo = _extract_metric_type_from_section(target_section)
    if not tipo:
        tipo = 'simples'
    logger.debug(f"Extracted tipo='{tipo}' for metric '{object_name}'")
    
    # Extract formula components
    formula, function_id, fact_id = _extract_formula_components(target_section)
    logger.debug(f"Extracted formula components for '{object_name}': formula={formula}, function_id={function_id}, fact_id={fact_id}")
    
    # For composite metrics, extract child metric IDs
    child_metric_ids = []
    if tipo == 'composto':
        child_metric_ids = _extract_child_metric_ids(target_section, anchor, soup)
        logger.debug(f"Extracted {len(child_metric_ids)} child metrics for composite metric '{object_name}'")
    
    return {
        'tipo': tipo,
        'formula': formula,
        'function_id': function_id,
        'fact_id': fact_id,
        'child_metric_ids': child_metric_ids
    }


# ============================================================================
# REFACTORED: extract_template_objects broken into focused sub-functions
# ============================================================================

def _find_template_table(section: BeautifulSoup) -> Optional[BeautifulSoup]:
    """
    Find the OBJETOS DE TEMPLATE table.
    
    Args:
        section: Section to search in
        
    Returns:
        Template table or None
    """
    for td in section.find_all('td'):
        text = td.get_text(strip=True)
        if TableHeaders.OBJETOS_RELATORIO in text or 'OBJETOS DE TEMPLATE' in text:
            logger.debug(f"Found 'OBJETOS DE TEMPLATE' text in td")
            
            # Look for a table that has the 4 headers
            current = td
            for table_idx in range(10):
                next_table = current.find_next('table')
                if next_table:
                    header_row = next_table.find('tr')
                    if header_row:
                        headers = [th.get_text(strip=True) for th in header_row.find_all(['td', 'th'])]
                        header_text_upper = ' '.join(headers[:10]).upper()
                        
                        has_objetos = 'OBJETOS DO RELAT' in header_text_upper or 'OBJETOS DO RELATORIO' in header_text_upper
                        has_linhas = TableHeaders.LINHAS in header_text_upper
                        has_colunas = TableHeaders.COLUNAS in header_text_upper
                        
                        if has_objetos and has_linhas and has_colunas:
                            logger.debug(f"Table {table_idx} has expected headers")
                            return next_table
                    
                    current = next_table
    
    return None


def _extract_linhas_attributes(data_row: BeautifulSoup, seen_attr_ids: set) -> List[Dict[str, str]]:
    """
    Extract attributes from LINHAS column.
    
    Args:
        data_row: Data row with 4 cells
        seen_attr_ids: Set of already seen attribute IDs
        
    Returns:
        List of attribute dicts
    """
    atributos = []
    cells = data_row.find_all('td', recursive=False)
    
    if len(cells) >= 4:
        linhas_cell = cells[1]
        
        for link in linhas_cell.find_all('a'):
            attr_name_on_dataset = link.get_text(strip=True)
            href = link.get('href', '')
            if attr_name_on_dataset:
                attr_id = None
                match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                if match:
                    attr_id = match.group(1)
                
                # Only add if not already seen
                if attr_id and attr_id not in seen_attr_ids:
                    seen_attr_ids.add(attr_id)
                    atributos.append({
                        'name_on_dataset': attr_name_on_dataset,
                        'href': href,
                        'id': attr_id
                    })
                elif not attr_id:
                    atributos.append({
                        'name_on_dataset': attr_name_on_dataset,
                        'href': href,
                        'id': attr_id
                    })
    
    return atributos


def _extract_colunas_metrics(data_row: BeautifulSoup, seen_metric_ids: set) -> List[Dict[str, str]]:
    """
    Extract metrics from COLUNAS column.
    
    Args:
        data_row: Data row with 4 cells
        seen_metric_ids: Set of already seen metric IDs
        
    Returns:
        List of metric dicts
    """
    metricas = []
    cells = data_row.find_all('td', recursive=False)
    
    if len(cells) >= 4:
        colunas_cell = cells[2]
        
        for link in colunas_cell.find_all('a'):
            metric_name_on_dataset = link.get_text(strip=True)
            href = link.get('href', '')
            if metric_name_on_dataset:
                metric_id = None
                match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                if match:
                    metric_id = match.group(1)
                
                # Only add if not already seen
                if metric_id and metric_id not in seen_metric_ids:
                    seen_metric_ids.add(metric_id)
                    metricas.append({
                        'name_on_dataset': metric_name_on_dataset,
                        'href': href,
                        'id': metric_id
                    })
                elif not metric_id:
                    metricas.append({
                        'name_on_dataset': metric_name_on_dataset,
                        'href': href,
                        'id': metric_id
                    })
    
    return metricas


def extract_template_objects(soup: BeautifulSoup, object_name: str, 
                            anchor: Optional[str] = None) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Extract attributes (rows) and metrics (columns) from OBJETOS DE TEMPLATE table.
    
    REFACTORED: Now uses focused sub-functions for better maintainability.
    
    Args:
        soup: BeautifulSoup object
        object_name: Name of object
        anchor: Optional anchor ID
        
    Returns:
        Tuple of (list of attribute dicts, list of metric dicts)
    """
    section = find_object_section(soup, object_name, anchor)
    if not section:
        logger.warning(f"Section not found for object: {object_name}, anchor: {anchor}")
        return [], []
    
    atributos = []
    metricas = []
    
    # Track IDs to avoid duplicates
    seen_attr_ids = set()
    seen_metric_ids = set()
    
    logger.debug(f"Searching for OBJETOS DE TEMPLATE in section for {object_name}")
    
    # Find OBJETOS DE TEMPLATE section
    template_table = _find_template_table(section)
    
    if template_table:
        # Find the data row
        header_row = template_table.find('tr')
        if header_row:
            data_row = header_row.find_next_sibling('tr')
            
            if not data_row:
                # Try finding all TRs
                all_rows = template_table.find_all('tr')
                for row in all_rows:
                    if row == header_row:
                        continue
                    cells = row.find_all('td', recursive=False)
                    if len(cells) == 4:
                        linhas_links = cells[1].find_all('a') if len(cells) > 1 else []
                        colunas_links = cells[2].find_all('a') if len(cells) > 2 else []
                        if linhas_links or colunas_links:
                            data_row = row
                            break
            
            if data_row:
                # Extract attributes and metrics
                atributos = _extract_linhas_attributes(data_row, seen_attr_ids)
                metricas = _extract_colunas_metrics(data_row, seen_metric_ids)
    
    return atributos, metricas


def find_metric_link(metrica_index_path: Path, metric_name: str, metric_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Find a metric link in Métrica.html index.
    
    Args:
        metrica_index_path: Path to Métrica.html
        metric_name: Name of the metric
        metric_id: Optional ID from HREF [$$$$ID$$$$] format for exact matching
    
    Returns:
        Dict with name, file, anchor, and href, or None if not found
    """
    if not metrica_index_path.exists():
        return None
    
    soup = parse_html_file(metrica_index_path)
    
    # First, try to find by ID if provided (most accurate)
    if metric_id:
        for link in soup.find_all('a', class_='MAINBODY'):
            href = link.get('href', '')
            # Check if anchor matches the ID
            parts = href.split('#')
            anchor = parts[1] if len(parts) > 1 else ''
            if anchor.upper() == metric_id.upper():
                # Use the name directly from HTML - it already has correct encoding
                link_name = link.get_text(strip=True)
                return {
                    'name': link_name,  # Official name from Métrica.html with correct accents
                    'file': parts[0] if parts else '',
                    'anchor': anchor,
                    'href': href
                }
    
    # Fallback: search by name (with accent normalization)
    import unicodedata
    def normalize_text(text):
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        return text.lower().strip()
    
    metric_name_norm = normalize_text(metric_name)
    
    for link in soup.find_all('a', class_='MAINBODY'):
        link_text = link.get_text(strip=True)
        link_text_norm = normalize_text(link_text)
        
        # Try exact match first
        if link_text_norm == metric_name_norm:
            href = link.get('href', '')
            parts = href.split('#')
            # Use the name directly from HTML - it already has correct encoding
            return {
                'name': link_text,  # Official name from Métrica.html with correct accents
                'file': parts[0] if parts else '',
                'anchor': parts[1] if len(parts) > 1 else '',
                'href': href
            }
        
        # Try partial match
        if metric_name_norm in link_text_norm or link_text_norm in metric_name_norm:
            href = link.get('href', '')
            parts = href.split('#')
            # Use the name directly from HTML - it already has correct encoding
            return {
                'name': link_text,  # Official name from Métrica.html with correct accents
                'file': parts[0] if parts else '',
                'anchor': parts[1] if len(parts) > 1 else '',
                'href': href
            }
    
    return None

