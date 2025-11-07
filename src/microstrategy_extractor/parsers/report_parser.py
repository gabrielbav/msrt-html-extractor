"""Report and dataset parsing utilities."""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup, Comment

from microstrategy_extractor.parsers.base_parser import parse_html_file, find_object_section
from microstrategy_extractor.utils.text_normalizer import TextNormalizer
from microstrategy_extractor.utils.logger import get_logger
from microstrategy_extractor.core.constants import HTMLSections, HTMLComments, HTMLImages, RegexPatterns
from microstrategy_extractor.core.exceptions import ParsingError

logger = get_logger(__name__)


def extract_report_links(documento_path: Path) -> List[Dict[str, str]]:
    """
    Extract all report links from Documento.html.
    
    Args:
        documento_path: Path to Documento.html
        
    Returns:
        List of dicts with 'name', 'file', 'anchor', 'href' keys
    """
    soup = parse_html_file(documento_path)
    reports = []
    
    # Find all links in the document list
    for link in soup.find_all('a', class_='MAINBODY'):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        if text and href:
            # Extract file and anchor from href (format: file.html#anchor)
            parts = href.split('#')
            file_name = parts[0] if parts else ''
            anchor = parts[1] if len(parts) > 1 else ''
            reports.append({
                'name': text,
                'file': file_name,
                'anchor': anchor,
                'href': href
            })
    
    return reports


def find_report_by_id(documento_path: Path, report_id: str) -> Optional[Dict[str, str]]:
    """
    Find a specific report by ID in Documento.html.
    
    Args:
        documento_path: Path to Documento.html
        report_id: Report ID to find
        
    Returns:
        Dict with 'name', 'file', 'anchor', 'href' or None
    """
    reports = extract_report_links(documento_path)
    
    # Try exact match on anchor ID
    for report in reports:
        if report.get('anchor', '') == report_id:
            return report
    
    return None


def find_report_by_name(documento_path: Path, report_name: str) -> List[Dict[str, str]]:
    """
    Find all reports with the given name in Documento.html.
    
    Returns a list of all reports that match the name (can be multiple reports with same name).
    
    Args:
        documento_path: Path to Documento.html
        report_name: Name of report to find
        
    Returns:
        List of matching report dicts
    """
    reports = extract_report_links(documento_path)
    matching_reports = []
    
    # First try exact match - collect ALL matching reports
    for report in reports:
        if report['name'] == report_name:
            matching_reports.append(report)
    
    if matching_reports:
        return matching_reports
    
    # Then try case-insensitive exact match
    report_name_lower = report_name.lower()
    for report in reports:
        if report['name'].lower() == report_name_lower:
            matching_reports.append(report)
    
    if matching_reports:
        return matching_reports
    
    # Try normalized comparison (handle encoding issues)
    report_name_norm = TextNormalizer.normalize_for_matching(report_name)
    
    # Try normalized exact match - collect ALL matching reports
    for report in reports:
        report_norm = TextNormalizer.normalize_for_matching(report['name'])
        if report_name_norm == report_norm:
            matching_reports.append(report)
    
    if matching_reports:
        return matching_reports
    
    # If no exact match, try fuzzy matching (return best match only)
    best_match = TextNormalizer.find_best_match(
        report_name,
        [r['name'] for r in reports]
    )
    
    if best_match:
        for report in reports:
            if report['name'] == best_match:
                return [report]
    
    return []


def extract_datasets_from_report(soup: BeautifulSoup, object_name: str, 
                                 anchor: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract datasets from DOCUMENT DEFINITION section of a report.
    
    Args:
        soup: BeautifulSoup object
        object_name: Name of the report object
        anchor: Optional anchor ID
        
    Returns:
        List of dataset dicts with 'name', 'id', 'href' keys
    """
    # Find the object section
    section = find_object_section(soup, object_name, anchor)
    if not section:
        return []
    
    datasets = []
    
    # Find DOCUMENT DEFINITION section
    for td in section.find_all('td'):
        text = td.get_text(strip=True)
        if HTMLSections.DOCUMENT_DEFINITION in text:
            # Find the next table with dataset links or text
            next_table = td.find_next('table')
            if next_table:
                # First, try to find links with dataset names
                for link in next_table.find_all('a'):
                    href = link.get('href', '')
                    name = link.get_text(strip=True)
                    if name and href:
                        # Fix common accent issues
                        name = TextNormalizer.fix_common_accents(name)
                        
                        # Extract ID from href placeholder format
                        dataset_id = None
                        match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                        if match:
                            dataset_id = match.group(1)
                        datasets.append({
                            'name': name,
                            'id': dataset_id,
                            'href': href
                        })
                
                # If no links found, try to extract dataset names from text
                if not datasets:
                    # Look for the "Datasets:" row
                    for row in next_table.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True)
                            if label.lower() == 'datasets:':
                                # Extract dataset names from the cell text
                                datasets_cell = cells[1]
                                text_content = datasets_cell.get_text()
                                
                                # Split by comma and clean up
                                dataset_names = [name.strip() for name in text_content.split(',') if name.strip()]
                                
                                # Create dataset entries (without ID since there are no links)
                                for name in dataset_names:
                                    name = TextNormalizer.fix_common_accents(name)
                                    datasets.append({
                                        'name': name,
                                        'id': None,
                                        'href': ''
                                    })
                                break
            # Only process the first DOCUMENT DEFINITION found
            break
    
    return datasets


def resolve_dataset_link(base_path: Path, dataset_id: str, 
                        cubo_inteligente_path: Path,
                        relatorio_path: Optional[Path] = None, 
                        atalho_path: Optional[Path] = None,
                        dataset_name: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """
    Resolve dataset ID or name to actual file path.
    
    Searches in CuboInteligente.html, Relatório.html, or Atalho.html.
    
    Args:
        base_path: Base path to HTML files
        dataset_id: Dataset ID to search for (can be empty if searching by name)
        cubo_inteligente_path: Path to CuboInteligente.html
        relatorio_path: Optional path to Relatório.html
        atalho_path: Optional path to Atalho.html
        dataset_name: Optional dataset name to search by
        
    Returns:
        Tuple of (file_path, source) where source is "CuboInteligente", "Documento", or "Shortcut"
        Returns None if not found
    """
    # First try CuboInteligente.html
    if cubo_inteligente_path.exists():
        soup = parse_html_file(cubo_inteligente_path)
        
        for link in soup.find_all('a'):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Match by ID if available
            if dataset_id and (f'#{dataset_id}' in href or dataset_id in href):
                parts = href.split('#')
                file_name = parts[0] if parts else ''
                anchor = parts[1] if len(parts) > 1 else dataset_id
                if anchor:
                    return (f"{file_name}#{anchor}", "CuboInteligente")
                return (file_name, "CuboInteligente")
            
            # Match by name if ID not available
            if dataset_name and link_text == dataset_name:
                parts = href.split('#')
                file_name = parts[0] if parts else ''
                anchor = parts[1] if len(parts) > 1 else ''
                if anchor:
                    return (f"{file_name}#{anchor}", "CuboInteligente")
                return (file_name, "CuboInteligente")
    
    # If not found in CuboInteligente, try Relatório.html
    if relatorio_path and relatorio_path.exists():
        soup = parse_html_file(relatorio_path)
        
        for link in soup.find_all('a'):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Match by ID if available
            if dataset_id and (f'#{dataset_id}' in href or dataset_id in href):
                parts = href.split('#')
                file_name = parts[0] if parts else ''
                anchor = parts[1] if len(parts) > 1 else dataset_id
                if anchor:
                    return (f"{file_name}#{anchor}", "Documento")
                return (file_name, "Documento")
            
            # Match by name if ID not available
            if dataset_name and link_text == dataset_name:
                parts = href.split('#')
                file_name = parts[0] if parts else ''
                anchor = parts[1] if len(parts) > 1 else ''
                if anchor:
                    return (f"{file_name}#{anchor}", "Documento")
                return (file_name, "Documento")
    
    # If not found, try Atalho.html
    if atalho_path and atalho_path.exists():
        soup = parse_html_file(atalho_path)
        
        for link in soup.find_all('a'):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Match by ID if available
            if dataset_id and (f'#{dataset_id}' in href or dataset_id in href):
                parts = href.split('#')
                file_name = parts[0] if parts else ''
                anchor = parts[1] if len(parts) > 1 else dataset_id
                if anchor:
                    return (f"{file_name}#{anchor}", "Shortcut")
                return (file_name, "Shortcut")
            
            # Match by name if ID not available
            if dataset_name and link_text == dataset_name:
                parts = href.split('#')
                file_name = parts[0] if parts else ''
                anchor = parts[1] if len(parts) > 1 else ''
                if anchor:
                    return (f"{file_name}#{anchor}", "Shortcut")
                return (file_name, "Shortcut")
    
    return None


def is_report_dataset(soup: BeautifulSoup, anchor: str) -> bool:
    """
    Check if a dataset is a Report (vs CuboInteligente) by looking for ViewReport.bmp image.
    
    Args:
        soup: BeautifulSoup object
        anchor: Dataset anchor ID
        
    Returns:
        True if dataset is a Report type
    """
    section = find_object_section(soup, "", anchor)
    if not section:
        return False
    
    # Look for ViewReport.bmp image in the section
    for img in section.find_all('img'):
        src = img.get('src', '')
        if HTMLImages.VIEW_REPORT in src:
            return True
    
    return False


def extract_graphic_type(soup: BeautifulSoup, anchor: str) -> Optional[str]:
    """
    Extract graphic type from OPÇÕES DO GRÁFICO section for Report datasets.
    
    Args:
        soup: BeautifulSoup object
        anchor: Dataset anchor ID
        
    Returns:
        Graphic type string or None
    """
    # Find the anchor tag first
    anchor_tag = soup.find('a', {'name': anchor})
    if not anchor_tag:
        logger.debug(f"Anchor tag not found: {anchor}")
        return None
    
    logger.debug(f"Searching for {HTMLSections.OPCOES_GRAFICO} after anchor")
    
    # Search forward from the anchor for OPÇÕES DO GRÁFICO section
    found_grafic_section = False
    current = anchor_tag
    for _ in range(2000):  # Search up to 2000 elements forward
        current = current.find_next()
        if not current:
            break
        
        # Stop if we hit another object (next anchor with a different ID)
        if current.name == 'a' and current.get('name') and current.get('name') != anchor:
            logger.debug(f"Reached next object ({current.get('name')}), stopping search")
            break
        
        if current.name == 'td':
            text = current.get_text(strip=True)
            
            # Check for exact section header
            text_norm = TextNormalizer.for_comparison(text)
            if text == HTMLSections.OPCOES_GRAFICO or text_norm == HTMLSections.OPCOES_GRAFICO_NORM:
                logger.debug(f"Found {HTMLSections.OPCOES_GRAFICO} section header")
                found_grafic_section = True
                continue
            
            # If we found the graphic section, look for "Tipo de gráfico" in rows
            if found_grafic_section or HTMLSections.OPCOES_GRAFICO_NORM in text_norm:
                parent_row = current.parent
                if parent_row and parent_row.name == 'tr':
                    cells = parent_row.find_all('td')
                    if len(cells) >= 2:
                        header = cells[0].get_text(strip=True)
                        header_norm = TextNormalizer.for_comparison(header).lower()
                        
                        if 'tipo' in header_norm and 'grafico' in header_norm:
                            value = cells[1].get_text(strip=True)
                            # Make sure it's a reasonable value
                            if value and 3 < len(value) < 50:
                                logger.debug(f"Found graphic type: {value}")
                                return value
    
    logger.debug(f"{HTMLSections.OPCOES_GRAFICO} or 'Tipo de gráfico' not found")
    return None


def extract_template_objects_report(soup: BeautifulSoup, anchor: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Extract attributes and metrics from Report format (using [ROWS] and [COLUMNS] markers).
    
    Report datasets have a different structure:
    - Attributes are in [ROWS] section
    - Metrics are in [COLUMNS] section
    
    Args:
        soup: BeautifulSoup object
        anchor: Dataset anchor ID
        
    Returns:
        Tuple of (list of attribute dicts, list of metric dicts)
    """
    section = find_object_section(soup, "", anchor)
    if not section:
        logger.warning(f"Section not found for anchor: {anchor}")
        return [], []
    
    atributos = []
    metricas = []
    
    # Get the HTML content as string to find comments
    section_html = str(section)
    
    # Find [ROWS] section for attributes
    if HTMLComments.ROWS_MARKER in section_html:
        logger.debug("Found [ROWS] section for attributes")
        soup_section = BeautifulSoup(section_html, 'lxml')
        for comment in soup_section.find_all(string=lambda text: isinstance(text, Comment)):
            if HTMLComments.ROWS_MARKER in str(comment):
                # Get the next TD after this comment
                next_elem = comment
                for _ in range(10):
                    next_elem = next_elem.find_next()
                    if next_elem and next_elem.name == 'td':
                        # Extract all links from this TD
                        for link in next_elem.find_all('a'):
                            name = link.get_text(strip=True)
                            href = link.get('href', '')
                            if name and href and '$$$$' in href:
                                attr_id = None
                                match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                                if match:
                                    attr_id = match.group(1)
                                
                                atributos.append({
                                    'name_on_dataset': name,
                                    'href': href,
                                    'id': attr_id
                                })
                        break
                break
    
    # Find [COLUMNS] section for metrics
    if HTMLComments.COLUMNS_MARKER in section_html:
        logger.debug("Found [COLUMNS] section for metrics")
        soup_section = BeautifulSoup(section_html, 'lxml')
        for comment in soup_section.find_all(string=lambda text: isinstance(text, Comment)):
            if HTMLComments.COLUMNS_MARKER in str(comment):
                # Get the next TD after this comment
                next_elem = comment
                for _ in range(10):
                    next_elem = next_elem.find_next()
                    if next_elem and next_elem.name == 'td':
                        # Extract all links from this TD
                        for link in next_elem.find_all('a'):
                            name = link.get_text(strip=True)
                            href = link.get('href', '')
                            if name and href and '$$$$' in href:
                                metric_id = None
                                match = re.search(RegexPatterns.ID_PLACEHOLDER, href)
                                if match:
                                    metric_id = match.group(1)
                                
                                metricas.append({
                                    'name_on_dataset': name,
                                    'href': href,
                                    'id': metric_id
                                })
                        break
                break
    
    logger.debug(f"Report format extracted: {len(atributos)} attributes, {len(metricas)} metrics")
    return atributos, metricas

