"""HTML parsing utilities for MicroStrategy documentation."""

import re
import unicodedata
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup, Comment, NavigableString

logger = logging.getLogger(__name__)


def normalize_for_comparison(text: str) -> str:
    """Normalize text for comparison, handling encoding issues.
    
    Removes accents and normalizes unicode to handle encoding problems
    in HTML files (e.g., 'EXPRESSÃO' vs 'EXPRESSÃ\x83O').
    """
    if not text:
        return ''
    # Normalize unicode and remove accents for comparison
    normalized = unicodedata.normalize('NFKD', text)
    # Remove combining characters (accents)
    ascii_text = ''.join(c for c in normalized if not unicodedata.combining(c))
    return ascii_text.upper()


def parse_html_file(file_path: Path) -> BeautifulSoup:
    """Parse an HTML file and return BeautifulSoup object.
    
    Tries multiple encodings to handle files with encoding issues.
    """
    # Try different encodings in order of likelihood
    encodings = ['iso-8859-1', 'latin-1', 'cp1252', 'utf-8', 'windows-1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            # If we got here, the encoding worked
            return BeautifulSoup(content, 'html.parser')
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Fallback: use utf-8 with errors='ignore'
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return BeautifulSoup(content, 'html.parser')


def find_object_section(soup: BeautifulSoup, object_name: str, anchor: Optional[str] = None) -> Optional[BeautifulSoup]:
    """Find an object section by name using [OBJECT: ...] comment markers or anchor.
    
    Returns a BeautifulSoup fragment containing only the specific object section,
    bounded by the object's anchor and the next object marker (OBJECT comment or next anchor).
    """
    # If anchor is provided, try to find by anchor first
    if anchor:
        anchor_tag = soup.find('a', {'name': anchor})
        if anchor_tag:
            logger.debug(f"Found anchor tag for: {anchor}")
            
            # Find the parent TR that contains this anchor (each object is in a TR)
            parent_tr = anchor_tag
            while parent_tr and parent_tr.name != 'tr':
                parent_tr = parent_tr.parent
            
            if parent_tr:
                # Return just this TR which contains the entire object section
                return parent_tr
    
    # Search for comments containing the object name
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment_text = str(comment)
        if f'[OBJECT: {object_name}]' in comment_text or f'[OBJECT: {object_name} ' in comment_text:
            # Find the parent table that contains this object
            parent = comment.parent
            while parent and parent.name != 'table':
                parent = parent.parent
            if parent:
                # Return the section starting from this table
                return parent.find_parent('table') or parent
    return None


def extract_report_links(documento_path: Path) -> List[Dict[str, str]]:
    """Extract all report links from Documento.html."""
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
    """Find a specific report by ID in Documento.html."""
    reports = extract_report_links(documento_path)
    
    # Try exact match on anchor ID
    for report in reports:
        if report.get('anchor', '') == report_id:
            return report
    
    return None


def find_report_by_name(documento_path: Path, report_name: str) -> List[Dict[str, str]]:
    """Find all reports with the given name in Documento.html.
    
    Returns a list of all reports that match the name (can be multiple reports with same name).
    """
    reports = extract_report_links(documento_path)
    matching_reports = []
    
    # First try exact match - collect ALL matching reports
    for report in reports:
        if report['name'] == report_name:
            matching_reports.append(report)
    
    # If found exact matches, return them
    if matching_reports:
        return matching_reports
    
    # Then try case-insensitive exact match
    report_name_lower = report_name.lower()
    for report in reports:
        if report['name'].lower() == report_name_lower:
            matching_reports.append(report)
    
    # If found case-insensitive matches, return them
    if matching_reports:
        return matching_reports
    
    # Try normalized comparison (handle encoding issues)
    import unicodedata
    def normalize_text(text):
        # Normalize unicode, remove accents, and convert to lowercase for comparison
        # This handles cases where HTML has "Lderes" but user searches for "Líderes"
        text = unicodedata.normalize('NFKD', text)
        # Remove combining characters (accents)
        text = ''.join(c for c in text if not unicodedata.combining(c))
        return text.lower().strip()
    
    report_name_norm = normalize_text(report_name)
    search_words = set(report_name_norm.split())
    best_match = None
    best_score = 0
    
    # Try normalized exact match - collect ALL matching reports
    for report in reports:
        report_norm = normalize_text(report['name'])
        if report_name_norm == report_norm:
            matching_reports.append(report)
    
    # If found normalized matches, return them
    if matching_reports:
        return matching_reports
    
    # If no exact match, try fuzzy matching (return best match only)
    # First, try to find reports where search term is contained in report name (more specific)
    for report in reports:
        report_norm = normalize_text(report['name'])
        if report_name_norm in report_norm:
            # Prefer matches that start with the search term or have more words in common
            score = len(report_name_norm) / len(report_norm) if report_norm else 0
            # Bonus for starting with search term
            if report_norm.startswith(report_name_norm):
                score += 0.5
            # Bonus for having more matching words
            report_words = set(report_norm.split())
            common_words = search_words.intersection(report_words)
            if common_words:
                score += len(common_words) * 0.1
            if score > best_score:
                best_score = score
                best_match = report
    
    if best_match:
        return [best_match]
    
    # If no exact match, try fuzzy matching based on common words
    # This handles cases where HTML has encoding issues (e.g., "Lderes" vs "Líderes")
    for report in reports:
        report_norm = normalize_text(report['name'])
        report_words = set(report_norm.split())
        common_words = search_words.intersection(report_words)
        if len(common_words) >= 3:  # At least 3 words in common
            score = len(common_words) / max(len(search_words), len(report_words))
            # Bonus if report name starts with search term prefix
            if report_norm.startswith('04.10.043'):
                score += 0.3
            if score > best_score:
                best_score = score
                best_match = report
    
    if best_match:
        return [best_match]
    
    return []


def fix_common_accents(text: str) -> str:
    """Fix common accent issues in text due to HTML encoding problems.
    
    Note: This is a minimal fallback. The correct approach is to use the name
    directly from the HTML file (Atributo.html, Métrica.html) which already
    has the correct encoding.
    """
    # Only fix the most critical cases that are known to be wrong
    # The proper solution is to use the name from the index HTML files
    minimal_corrections = {
        'Ms ': 'Mês ',
        'Lderes': 'Líderes',
    }
    
    result = text
    for wrong, correct in minimal_corrections.items():
        result = result.replace(wrong, correct)
    
    return result


def extract_datasets_from_report(soup: BeautifulSoup, object_name: str, anchor: Optional[str] = None) -> List[Dict[str, str]]:
    """Extract datasets from DOCUMENT DEFINITION section of a report."""
    # Find the object section
    section = find_object_section(soup, object_name, anchor)
    if not section:
        return []
    
    datasets = []
    
    # Find DOCUMENT DEFINITION section - it can be in a td with or without SECTIONHEADER class
    for td in section.find_all('td'):
        text = td.get_text(strip=True)
        if 'DOCUMENT DEFINITION' in text:
            # Find the next table with dataset links or text
            next_table = td.find_next('table')
            if next_table:
                # First, try to find links with dataset names
                for link in next_table.find_all('a'):
                    href = link.get('href', '')
                    name = link.get_text(strip=True)
                    if name and href:
                        # Fix common accent issues
                        name = fix_common_accents(name)
                        
                        # Extract ID from href placeholder format [$$$$ID$$$$]
                        dataset_id = None
                        match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                        if match:
                            dataset_id = match.group(1)
                        datasets.append({
                            'name': name,
                            'id': dataset_id,
                            'href': href
                        })
                
                # If no links found, try to extract dataset names from text (without links)
                if not datasets:
                    # Look for the "Datasets:" row
                    for row in next_table.find_all('tr'):
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True)
                            if label.lower() == 'datasets:':
                                # Extract dataset names from the cell text
                                # Datasets are separated by commas, and may have IMG tags before them
                                datasets_cell = cells[1]
                                
                                # Get all text content, split by commas
                                text_content = datasets_cell.get_text()
                                
                                # Split by comma and clean up
                                dataset_names = [name.strip() for name in text_content.split(',') if name.strip()]
                                
                                # Create dataset entries (without ID since there are no links)
                                for name in dataset_names:
                                    # Fix common accent issues
                                    name = fix_common_accents(name)
                                    datasets.append({
                                        'name': name,
                                        'id': None,  # No ID available when dataset is just text
                                        'href': ''
                                    })
                                break
            # Only process the first DOCUMENT DEFINITION found in this section
            break
    
    return datasets


def resolve_dataset_link(base_path: Path, dataset_id: str, cubo_inteligente_path: Path, relatorio_path: Optional[Path] = None, atalho_path: Optional[Path] = None, dataset_name: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """Resolve dataset ID or name to actual file path using CuboInteligente.html, Relatório.html or Atalho.html.
    
    If dataset is a cube, look in CuboInteligente.html.
    If dataset is a report, look in Relatório.html (Documento.html).
    If dataset is a shortcut, look in Atalho.html.
    
    Args:
        base_path: Base path to HTML files
        dataset_id: Dataset ID to search for (can be empty if searching by name)
        cubo_inteligente_path: Path to CuboInteligente.html
        relatorio_path: Optional path to Relatório.html
        atalho_path: Optional path to Atalho.html
        dataset_name: Optional dataset name to search by (used when ID is not available)
    
    Returns:
        Tuple of (file_path, source) where source is "CuboInteligente", "Documento", or "Shortcut", or None if not found
    """
    # First try CuboInteligente.html
    if cubo_inteligente_path.exists():
        soup = parse_html_file(cubo_inteligente_path)
        
        # Find link with anchor matching the dataset_id or name
        for link in soup.find_all('a'):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Match by ID if available
            if dataset_id and (f'#{dataset_id}' in href or dataset_id in href):
                # Extract file name and anchor from href
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
    
    # If not found in CuboInteligente, try Relatório.html (Documento.html)
    if relatorio_path and relatorio_path.exists():
        soup = parse_html_file(relatorio_path)
        
        # Find link with anchor matching the dataset_id or name
        for link in soup.find_all('a'):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Match by ID if available
            if dataset_id and (f'#{dataset_id}' in href or dataset_id in href):
                # Extract file name and anchor from href
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
    
    # If not found in CuboInteligente or Relatório, try Atalho.html
    if atalho_path and atalho_path.exists():
        soup = parse_html_file(atalho_path)
        
        # Find link with anchor matching the dataset_id or name
        for link in soup.find_all('a'):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            # Match by ID if available
            if dataset_id and (f'#{dataset_id}' in href or dataset_id in href):
                # Extract file name and anchor from href
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
    """Check if a dataset is a Report (vs CuboInteligente) by looking for ViewReport.bmp image."""
    section = find_object_section(soup, "", anchor)
    if not section:
        return False
    
    # Look for ViewReport.bmp image in the section
    for img in section.find_all('img'):
        src = img.get('src', '')
        if 'ViewReport' in src:
            return True
    
    return False


def extract_graphic_type(soup: BeautifulSoup, anchor: str) -> Optional[str]:
    """Extract graphic type from OPÇÕES DO GRÁFICO section for Report datasets."""
    # Find the anchor tag first
    anchor_tag = soup.find('a', {'name': anchor})
    if not anchor_tag:
        logger.debug(f"Anchor tag not found: {anchor}")
        return None
    
    logger.debug(f"Searching for OPÇÕES DO GRÁFICO after anchor")
    
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
            
            # Check for exact "OPÇÕES DO GRÁFICO" section header
            if text == 'OPÇÕES DO GRÁFICO' or normalize_for_comparison(text).upper() == 'OPCOES DO GRAFICO':
                logger.debug(f"Found OPÇÕES DO GRÁFICO section header")
                found_grafic_section = True
                # Continue searching for the table with options
                continue
            
            # If we found the graphic section, look for "Tipo de gráfico" in rows
            if found_grafic_section or 'OPCOES DO GRAFICO' in normalize_for_comparison(text).upper():
                # Check if this TD is part of a row with "Tipo de gráfico"
                parent_row = current.parent
                if parent_row and parent_row.name == 'tr':
                    cells = parent_row.find_all('td')
                    if len(cells) >= 2:
                        header = cells[0].get_text(strip=True)
                        header_norm = normalize_for_comparison(header).lower()
                        
                        if 'tipo' in header_norm and 'grafico' in header_norm:
                            value = cells[1].get_text(strip=True)
                            # Make sure it's a reasonable value (not a whole section of text)
                            if value and 3 < len(value) < 50:
                                logger.debug(f"Found graphic type: {value}")
                                return value
    
    logger.debug(f"OPÇÕES DO GRÁFICO or 'Tipo de gráfico' not found")
    return None


def extract_template_objects_report(soup: BeautifulSoup, anchor: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Extract attributes and metrics from Report format (using [ROWS] and [COLUMNS] markers).
    
    Report datasets have a different structure:
    - Attributes are in <!---------- [ROWS] ----------> section
    - Metrics are in <!---------- [COLUMNS] ----------> section
    
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
    if '[ROWS]' in section_html:
        logger.debug("Found [ROWS] section for attributes")
        # Find the comment and get elements after it
        soup_section = BeautifulSoup(section_html, 'lxml')
        for comment in soup_section.find_all(string=lambda text: isinstance(text, Comment)):
            if '[ROWS]' in str(comment):
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
                                match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
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
    if '[COLUMNS]' in section_html:
        logger.debug("Found [COLUMNS] section for metrics")
        soup_section = BeautifulSoup(section_html, 'lxml')
        for comment in soup_section.find_all(string=lambda text: isinstance(text, Comment)):
            if '[COLUMNS]' in str(comment):
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
                                match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
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


def extract_template_objects(soup: BeautifulSoup, object_name: str, anchor: Optional[str] = None) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Extract attributes (rows) and metrics (columns) from OBJETOS DE TEMPLATE table.
    
    Returns:
        Tuple of (list of attribute dicts with name and href, list of metric dicts with name and href)
    """
    section = find_object_section(soup, object_name, anchor)
    if not section:
        logger.warning(f"Section not found for object: {object_name}, anchor: {anchor}")
        return [], []
    
    atributos = []
    metricas = []
    
    # Track IDs to avoid duplicates across multiple sections
    seen_attr_ids = set()
    seen_metric_ids = set()
    
    logger.debug(f"Searching for OBJETOS DE TEMPLATE in section for {object_name}")
    
    # Find OBJETOS DE TEMPLATE section
    template_table_found = None
    for td in section.find_all('td'):
        text = td.get_text(strip=True)
        if 'OBJETOS DE TEMPLATE' in text:
            logger.debug(f"Found 'OBJETOS DE TEMPLATE' text in td")
            # Find the template table - it has columns for LINHAS and COLUNAS
            # The structure is: header row with 4 columns, then data row with 4 TD cells
            # Each TD cell contains a nested table with the actual objects
            # Look for a table that has exactly these headers: OBJETOS DO RELATÓRIO, LINHAS, COLUNAS, PAGINAR POR
            current = td
            for table_idx in range(10):  # Search up to 10 tables ahead
                next_table = current.find_next('table')
                if next_table:
                    # Find header row to identify column positions
                    header_row = next_table.find('tr')
                    if header_row:
                        headers = [th.get_text(strip=True) for th in header_row.find_all(['td', 'th'])]
                        
                        # Check if this is the correct table - look for the 4 specific headers
                        # The headers should be: OBJETOS DO RELATÓRIO, LINHAS, COLUNAS, PAGINAR POR
                        header_text_upper = ' '.join(headers[:10]).upper()
                        has_objetos = 'OBJETOS DO RELAT' in header_text_upper or 'OBJETOS DO RELATORIO' in header_text_upper
                        has_linhas = 'LINHAS' in header_text_upper
                        has_colunas = 'COLUNAS' in header_text_upper
                        
                        if has_objetos and has_linhas and has_colunas:
                            logger.debug(f"Table {table_idx} has expected headers")
                            template_table_found = next_table
                            # Find the data row - try multiple approaches
                            data_row = None
                            
                            # Approach 1: Try find_next_sibling
                            data_row = header_row.find_next_sibling('tr')
                            
                            # Approach 2: Find all TRs and look for one with 4 TD cells that has links
                            if not data_row:
                                all_rows = next_table.find_all('tr')
                                for row in all_rows:
                                    if row == header_row:
                                        continue
                                    cells = row.find_all('td', recursive=False)
                                    if len(cells) == 4:
                                        # Check if this row has links in LINHAS or COLUNAS columns
                                        linhas_links = cells[1].find_all('a') if len(cells) > 1 else []
                                        colunas_links = cells[2].find_all('a') if len(cells) > 2 else []
                                        if linhas_links or colunas_links:
                                            data_row = row
                                            break
                            
                            if data_row:
                                cells = data_row.find_all('td', recursive=False)
                                logger.debug(f"Data row has {len(cells)} cells")
                                # We want the row that has 4 TD cells (OBJETOS, LINHAS, COLUNAS, PAGINAR POR)
                                if len(cells) == 4:
                                    # Extract attributes from LINHAS column (index 1)
                                    linhas_cell = cells[1]
                                    colunas_cell = cells[2]
                                    
                                    # Count links in each cell
                                    linhas_links_count = len(linhas_cell.find_all('a'))
                                    colunas_links_count = len(colunas_cell.find_all('a'))
                                    logger.debug(f"LINHAS cell has {linhas_links_count} links, COLUNAS cell has {colunas_links_count} links")
                                    
                                    # Find all links in this cell and nested tables (attributes)
                                    for link in linhas_cell.find_all('a'):
                                        attr_name_on_dataset = link.get_text(strip=True)
                                        href = link.get('href', '')
                                        if attr_name_on_dataset:
                                            # Extract ID from href placeholder format [$$$$ID$$$$]
                                            attr_id = None
                                            match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                                            if match:
                                                attr_id = match.group(1)
                                            
                                            # Only add if not already seen
                                            if attr_id and attr_id not in seen_attr_ids:
                                                seen_attr_ids.add(attr_id)
                                                atributos.append({
                                                    'name_on_dataset': attr_name_on_dataset,  # Name as found in dataset
                                                    'href': href,
                                                    'id': attr_id
                                                })
                                            elif not attr_id:  # No ID, add by name (less reliable)
                                                atributos.append({
                                                    'name_on_dataset': attr_name_on_dataset,
                                                    'href': href,
                                                    'id': attr_id
                                                })
                                    
                                    # Extract metrics from COLUNAS column (index 2)
                                    colunas_cell = cells[2]
                                    # Find all links in this cell and nested tables (metrics)
                                    for link in colunas_cell.find_all('a'):
                                        metric_name_on_dataset = link.get_text(strip=True)
                                        href = link.get('href', '')
                                        if metric_name_on_dataset:
                                            # Extract ID from href placeholder format [$$$$ID$$$$]
                                            metric_id = None
                                            match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                                            if match:
                                                metric_id = match.group(1)
                                            
                                            # Only add if not already seen
                                            if metric_id and metric_id not in seen_metric_ids:
                                                seen_metric_ids.add(metric_id)
                                                metricas.append({
                                                    'name_on_dataset': metric_name_on_dataset,  # Name as found in dataset
                                                    'href': href,
                                                    'id': metric_id
                                                })
                                            elif not metric_id:  # No ID, add by name (less reliable)
                                                metricas.append({
                                                    'name_on_dataset': metric_name_on_dataset,
                                                    'href': href,
                                                    'id': metric_id
                                                })
                                    
                                    # Only process the first matching row
                                    break
                    
                    current = next_table
            
            # If we didn't find the standard 4-column format, try alternative format
            # where all links are in a single cell
            if not atributos and not metricas and template_table_found:
                logger.debug("Standard format not found, trying alternative format (single cell with all links)")
                atributos, metricas = _extract_template_objects_alternative(template_table_found)
            
            # Don't break - there might be multiple OBJETOS DE TEMPLATE sections
            # We'll process all of them and combine the results
            # break  # REMOVED - process all sections
    
    return atributos, metricas


def _extract_template_objects_alternative(table: BeautifulSoup) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Extract attributes and metrics from alternative format where all links are in one cell.
    
    In this format, the first row contains all links mixed together:
    - Links appear twice (once for display, once for PAGINAR POR)
    - First half: attributes + metrics
    - Second half: same sequence repeated
    - Attributes: descriptive names (Mês, Ramo, Agência, etc.)
    - Metrics: usually start with "Vl." or end with "(%)"
    """
    atributos = []
    metricas = []
    
    # Get all links from the table
    all_links = table.find_all('a')
    if not all_links:
        return atributos, metricas
    
    # Since links appear twice, take only the first half
    total_links = len(all_links)
    unique_links = all_links[:total_links // 2] if total_links >= 2 else all_links
    
    logger.debug(f"Alternative format: Found {len(all_links)} total links, processing {len(unique_links)} unique")
    
    # Separate attributes from metrics based on naming patterns
    for link in unique_links:
        name = link.get_text(strip=True)
        href = link.get('href', '')
        
        if not name:
            continue
        
        # Extract ID from href placeholder format [$$$$ID$$$$]
        obj_id = None
        match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
        if match:
            obj_id = match.group(1)
        
        # Classify as attribute or metric based on naming patterns
        is_metric = (
            name.startswith('Vl.') or
            name.startswith('Valor') or
            name.endswith('(%)') or
            'Sinistralidade' in name or
            'Margem' in name or
            'Taxa' in name or
            'Índice' in name or
            'Razão' in name or
            'Percentual' in name or
            'Qtd.' in name or
            'Quantidade' in name
        )
        
        item = {
            'name_on_dataset': name,
            'href': href,
            'id': obj_id
        }
        
        if is_metric:
            metricas.append(item)
        else:
            atributos.append(item)
    
    logger.debug(f"Alternative format extracted: {len(atributos)} attributes, {len(metricas)} metrics")
    
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


def find_function_link(funcao_index_path: Path, function_id: str) -> Optional[Dict[str, str]]:
    """Find a function link in Função.html index by ID.
    
    Args:
        funcao_index_path: Path to Função.html
        function_id: ID from HREF [$$$$ID$$$$] format
    
    Returns:
        Dict with name, file, anchor, and href, or None if not found
    """
    if not funcao_index_path.exists():
        return None
    
    soup = parse_html_file(funcao_index_path)
    
    # Search by ID (most accurate)
    for link in soup.find_all('a', class_='MAINBODY'):
        href = link.get('href', '')
        # Check if anchor matches the ID
        parts = href.split('#')
        anchor = parts[1] if len(parts) > 1 else ''
        if anchor.upper() == function_id.upper():
            return {
                'name': link.get_text(strip=True),
                'file': parts[0] if parts else '',
                'anchor': anchor,
                'href': href
            }
    
    return None


def find_fact_link(fato_index_path: Path, fact_name: Optional[str] = None, fact_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Find a fact link in Fato.html index.
    
    Args:
        fato_index_path: Path to Fato.html
        fact_name: Optional name of the fact
        fact_id: Optional ID from HREF [$$$$ID$$$$] format for exact matching
    
    Returns:
        Dict with name, file, anchor, and href, or None if not found
    """
    if not fato_index_path.exists():
        return None
    
    soup = parse_html_file(fato_index_path)
    
    # First, try to find by ID if provided (most accurate)
    if fact_id:
        for link in soup.find_all('a', class_='MAINBODY'):
            href = link.get('href', '')
            # Check if anchor matches the ID
            parts = href.split('#')
            anchor = parts[1] if len(parts) > 1 else ''
            if anchor.upper() == fact_id.upper():
                return {
                    'name': link.get_text(strip=True),
                    'file': parts[0] if parts else '',
                    'anchor': anchor,
                    'href': href
                }
    
    # Fallback: search by name
    if fact_name:
        for link in soup.find_all('a', class_='MAINBODY'):
            if fact_name in link.get_text() or link.get_text() in fact_name:
                href = link.get('href', '')
                parts = href.split('#')
                return {
                    'name': link.get_text(strip=True),
                    'file': parts[0] if parts else '',
                    'anchor': parts[1] if len(parts) > 1 else '',
                    'href': href
                }
    
    return None


def find_attribute_link(atributo_index_path: Path, attribute_name: str, attribute_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Find an attribute link in Atributo.html index.
    
    Args:
        atributo_index_path: Path to Atributo.html
        attribute_name: Name of the attribute
        attribute_id: Optional ID from HREF [$$$$ID$$$$] format for exact matching
    
    Returns:
        Dict with name, file, anchor, and href, or None if not found
    """
    if not atributo_index_path.exists():
        return None
    
    soup = parse_html_file(atributo_index_path)
    
    # First, try to find by ID if provided (most accurate)
    if attribute_id:
        for link in soup.find_all('a', class_='MAINBODY'):
            href = link.get('href', '')
            # Check if anchor matches the ID
            parts = href.split('#')
            anchor = parts[1] if len(parts) > 1 else ''
            if anchor.upper() == attribute_id.upper():
                # Use the name directly from HTML - it already has correct encoding
                link_name = link.get_text(strip=True)
                return {
                    'name': link_name,  # Official name from Atributo.html with correct accents
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
    
    attribute_name_norm = normalize_text(attribute_name)
    
    for link in soup.find_all('a', class_='MAINBODY'):
        link_text = link.get_text(strip=True)
        link_text_norm = normalize_text(link_text)
        
        # Try exact match first
        if link_text_norm == attribute_name_norm:
            href = link.get('href', '')
            parts = href.split('#')
            # Use the name directly from HTML - it already has correct encoding
            return {
                'name': link_text,  # Official name from Atributo.html with correct accents
                'file': parts[0] if parts else '',
                'anchor': parts[1] if len(parts) > 1 else '',
                'href': href
            }
        
        # Try partial match
        if attribute_name_norm in link_text_norm or link_text_norm in attribute_name_norm:
            href = link.get('href', '')
            parts = href.split('#')
            # Use the name directly from HTML - it already has correct encoding
            return {
                'name': link_text,  # Official name from Atributo.html with correct accents
                'file': parts[0] if parts else '',
                'anchor': parts[1] if len(parts) > 1 else '',
                'href': href
            }
    
    return None


def extract_metric_definition(soup: BeautifulSoup, object_name: str, anchor: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Extract metric definition: tipo (simples/composto), formula, function_id, and fact_id.
    
    Looks for "Tipo de métrica" field in the DEFINIÇÃO section.
    The DEFINIÇÃO section is identified by a TABLE with CLASS=SECTIONHEADER containing "DEFINIÇÃO".
    For simple metrics, also extracts Function and Fact IDs from the formula row.
    """
    tipo = None
    formula = None
    function_id = None
    fact_id = None
    
    # First, try to find the object section using find_object_section
    # This ensures we're looking in the correct metric's section
    section = find_object_section(soup, object_name, anchor)
    search_area = section if section else soup
    
    # If anchor is provided, find the anchor first
    anchor_tag = None
    if anchor:
        anchor_tag = search_area.find('a', {'name': anchor})
        if not anchor_tag:
            anchor_tag = soup.find('a', {'name': anchor})
    
    # Find all DEFINIÇÃO sections within the search area - look for TABLE with CLASS=SECTIONHEADER containing "DEFINIÇÃO"
    def_sections = []
    for table in search_area.find_all('table', class_='SECTIONHEADER'):
        header_text = table.get_text(strip=True).upper()
        if 'DEFINIÇÃO' in header_text:
            def_sections.append(table)
    
    # If no sections found in search_area, search entire document
    if not def_sections:
        for table in soup.find_all('table', class_='SECTIONHEADER'):
            header_text = table.get_text(strip=True).upper()
            if 'DEFINIÇÃO' in header_text:
                def_sections.append(table)
    
    # If we have an anchor, find the DEFINIÇÃO section that comes after it
    # Use a more reliable approach: navigate from the anchor through the DOM tree
    target_section = None
    if anchor_tag and def_sections:
        # Find the parent table structure that contains this anchor
        anchor_parent = anchor_tag.find_parent('table')
        
        # Strategy: Start from the anchor and navigate forward through siblings and next elements
        # to find the DEFINIÇÃO section that belongs to this specific metric
        
        # First, try to find DEFINIÇÃO within the same parent structure as the anchor
        if anchor_parent:
            # Look for DEFINIÇÃO in the same parent or its siblings
            current = anchor_tag
            found_def = None
            
            # Navigate forward from the anchor
            while current:
                # Check if current element or its next siblings contain DEFINIÇÃO
                next_elem = current.find_next()
                while next_elem:
                    if next_elem.name == 'table' and 'SECTIONHEADER' in str(next_elem.get('class', [])):
                        header_text = next_elem.get_text(strip=True).upper()
                        if 'DEFINIÇÃO' in header_text:
                            found_def = next_elem
                            break
                    # Also check descendants
                    for def_table in next_elem.find_all('table', class_='SECTIONHEADER'):
                        header_text = def_table.get_text(strip=True).upper()
                        if 'DEFINIÇÃO' in header_text:
                            found_def = def_table
                            break
                    if found_def:
                        break
                    next_elem = next_elem.find_next()
                
                if found_def:
                    break
                
                # Move to parent and continue
                current = current.find_parent()
                if current == anchor_parent or not current:
                    break
            
            if found_def:
                target_section = found_def
        
        # If not found in parent structure, use the first DEFINIÇÃO after the anchor in document order
        if not target_section:
            # Use a simpler approach: find the first DEFINIÇÃO that appears after the anchor
            # by checking if anchor comes before DEFINIÇÃO in the document
            anchor_pos = None
            for elem in soup.descendants:
                if elem == anchor_tag:
                    anchor_pos = True
                elif anchor_pos and elem.name == 'table' and 'SECTIONHEADER' in str(elem.get('class', [])):
                    header_text = elem.get_text(strip=True).upper()
                    if 'DEFINIÇÃO' in header_text:
                        target_section = elem
                        break
    
    # If no target found yet, use the first DEFINIÇÃO
    if not target_section and def_sections:
        target_section = def_sections[0]
    
    if target_section:
        # Find the next table after the SECTIONHEADER (this contains the definition fields)
        # Skip empty tables between SECTIONHEADER and the actual data table
        # Use find_next() to search through all following elements, not just siblings
        current = target_section.find_next('table')
        while current:
            # Check if this table has rows with data
            rows = current.find_all('tr')
            if rows:
                # This is likely the data table
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        
                        # Look for "Tipo de métrica" or variations
                        label_upper = label.upper()
                        if 'TIPO' in label_upper and ('MÉTRICA' in label_upper or 'METRICA' in label_upper):
                            value_lower = value.lower()
                            if 'composto' in value_lower or 'composite' in value_lower:
                                tipo = 'composto'
                            else:
                                tipo = 'simples'
                        
                        # Look for Fórmula - extract text from the cell, including links
                        if 'FÓRMULA' in label_upper or 'FORMULA' in label_upper:
                            formula_cell = cells[1]
                            # Extract formula text more carefully to avoid duplication
                            # We'll build the formula by processing elements in order, but only once
                            formula_parts = []
                            seen_elements = set()  # Track seen elements to avoid duplication
                            
                            # Process all elements in the formula cell in order
                            # We need to find links and their associated images
                            # Process all descendants in order, tracking the last image seen
                            last_img = None
                            for elem in formula_cell.descendants:
                                if isinstance(elem, str):
                                    text = elem.strip()
                                    # Add parentheses and meaningful text
                                    if text:
                                        # Always add parentheses
                                        if text in ['(', ')']:
                                            formula_parts.append(text)
                                        # For other text, avoid duplicates
                                        elif text not in [' ', ''] and text not in seen_elements:
                                            formula_parts.append(text)
                                            seen_elements.add(text)
                                elif hasattr(elem, 'name'):
                                    if elem.name == 'img':
                                        last_img = elem
                                    elif elem.name == 'a':
                                        link_text = elem.get_text(strip=True)
                                        # Only add link text once to avoid duplication
                                        if link_text and link_text not in seen_elements:
                                            formula_parts.append(link_text)
                                            seen_elements.add(link_text)
                                        # Extract ID from HREF if present (for Function and Fact)
                                        href = elem.get('href', '')
                                        if href:
                                            match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                                            if match:
                                                extracted_id = match.group(1)
                                                # Use the last image we encountered before this link
                                                if last_img:
                                                    img_src = last_img.get('src', '').lower()
                                                    if 'function.bmp' in img_src or 'function' in img_src:
                                                        if function_id is None:  # Only set if not already set
                                                            function_id = extracted_id
                                                    elif 'fact.bmp' in img_src or 'fact' in img_src:
                                                        if fact_id is None:  # Only set if not already set
                                                            fact_id = extracted_id
                                                else:
                                                    # Fallback: first link is usually Function, second is Fact
                                                    if function_id is None:
                                                        function_id = extracted_id
                                                    elif fact_id is None:
                                                        fact_id = extracted_id
                            
                            # Join formula parts, but be smarter about it
                            # Remove consecutive duplicates more intelligently
                            cleaned_parts = []
                            prev = None
                            prev2 = None  # Track two previous to catch patterns like "Sum Sum"
                            for part in formula_parts:
                                # Skip if it's a duplicate of the previous part (unless it's an operator)
                                if part != prev or part in ['(', ')', '/', '+', '-', '*']:
                                    # Also skip if we have a pattern like "Sum Sum" or "Metric Metric"
                                    if not (part == prev and part == prev2):
                                        cleaned_parts.append(part)
                                prev2 = prev
                                prev = part
                            
                            formula = ' '.join(cleaned_parts) if cleaned_parts else value
                            # Clean up extra spaces and normalize
                            formula = re.sub(r'\s+', ' ', formula).strip()
                            # Remove duplicate words/phrases (simple heuristic)
                            words = formula.split()
                            unique_words = []
                            prev_word = None
                            prev_word2 = None
                            for word in words:
                                # Skip if duplicate, unless it's an operator or parenthesis
                                if word != prev_word or word in ['(', ')', '/', '+', '-', '*']:
                                    # Also skip patterns like "Sum Sum" or "Metric Metric"
                                    if not (word == prev_word and word == prev_word2):
                                        unique_words.append(word)
                                prev_word2 = prev_word
                                prev_word = word
                            formula = ' '.join(unique_words)
                            # Remove spaces around parentheses, but add space after function name
                            formula = re.sub(r'\s*\(\s*', ' (', formula)
                            formula = re.sub(r'\s*\)\s*', ')', formula)
                
                # If we found tipo or formula, we're done
                if tipo is not None or formula is not None:
                    break
            
            # Find next table, but stop if we hit another SECTIONHEADER
            next_elem = current.find_next()
            if next_elem and next_elem.name == 'table' and 'SECTIONHEADER' in str(next_elem.get('class', [])):
                break  # Hit another section, stop
            current = current.find_next('table')
    
    # Default to 'simples' if tipo not found
    if not tipo:
        tipo = 'simples'
    
    # For composite metrics, extract child metric IDs
    child_metric_ids = []
    if tipo == 'composto' and target_section:
        # Look for child metrics ONLY in the formula section
        # The formula section contains all the child metrics we need
        # Process only the FIRST formula section we find after DEFINIÇÃO
        formula_processed = False
        current = target_section.find_next('table')
        while current and not formula_processed:
            rows = current.find_all('tr')
            if rows:
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True)
                        # Check for Metric Formula section or Fórmula field
                        if 'FÓRMULA' in label.upper() or 'FORMULA' in label.upper():
                            formula_cell = cells[1]
                            # Look for links with Metric.bmp (child metrics)
                            # Process elements in order to correctly associate images with links
                            # We need to track the previous sibling image for each link
                            for link in formula_cell.find_all('a'):
                                href = link.get('href', '')
                                if href and '[$$$$' in href:
                                    # Find the previous image sibling (could be previous_sibling or in previous elements)
                                    prev_img = None
                                    # Check previous sibling
                                    prev = link.previous_sibling
                                    while prev:
                                        if hasattr(prev, 'name') and prev.name == 'img':
                                            prev_img = prev
                                            break
                                        prev = prev.previous_sibling
                                    
                                    # If not found, check previous elements in the parent
                                    if not prev_img:
                                        for elem in formula_cell.descendants:
                                            if elem == link:
                                                break
                                            if hasattr(elem, 'name') and elem.name == 'img':
                                                prev_img = elem
                                    
                                    # Check if this is a metric link
                                    if prev_img:
                                        img_src = prev_img.get('src', '').lower()
                                        if 'metric.bmp' in img_src or 'metric' in img_src:
                                            match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                                            if match:
                                                metric_id = match.group(1)
                                                if metric_id not in child_metric_ids:
                                                    child_metric_ids.append(metric_id)
                            # Mark formula as processed and stop looking for more
                            formula_processed = True
                            break
            if not formula_processed:
                current = current.find_next('table')
                # Stop if we hit another SECTIONHEADER
                next_elem = current.find_next() if current else None
                if next_elem and next_elem.name == 'table' and 'SECTIONHEADER' in str(next_elem.get('class', [])):
                    break
            else:
                break
        
        # Only look for EMBEDDED METRIC sections if we didn't find any metrics in the formula
        # This handles cases where the formula is complex and metrics are in EMBEDDED sections
        if len(child_metric_ids) == 0 and anchor_tag:
            # Find all anchors to determine the range
            all_anchors = soup.find_all('a', {'name': True})
            anchor_index = None
            next_anchor_index = None
            
            # Get all elements in document order
            all_elements = list(soup.descendants)
            try:
                anchor_index = all_elements.index(anchor_tag)
                # Find the next anchor after this one
                for next_anchor in all_anchors:
                    try:
                        next_idx = all_elements.index(next_anchor)
                        if next_idx > anchor_index:
                            if next_anchor_index is None or next_idx < next_anchor_index:
                                next_anchor_index = next_idx
                    except ValueError:
                        continue
            except ValueError:
                pass
            
            # Search for EMBEDDED METRIC comments within the range
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment_text = str(comment).upper()
                if 'EMBEDDED METRIC' in comment_text or 'EMBEDDEDMETRIC' in comment_text:
                    # Check if this comment is within our range
                    try:
                        comment_index = all_elements.index(comment)
                        if anchor_index is not None:
                            if comment_index < anchor_index:
                                continue  # Before our anchor, skip
                            if next_anchor_index is not None and comment_index >= next_anchor_index:
                                continue  # After next anchor, skip
                    except ValueError:
                        continue
                    
                    # Find the table or structure after this comment
                    parent = comment.parent
                    while parent and parent.name != 'table':
                        parent = parent.parent
                    if parent:
                        # Look for links with Metric.bmp in this section
                        for link in parent.find_all('a'):
                            href = link.get('href', '')
                            if href and '[$$$$' in href:
                                # Find previous image
                                prev_img = link.find_previous('img')
                                if prev_img:
                                    img_src = prev_img.get('src', '').lower()
                                    if 'metric.bmp' in img_src or 'metric' in img_src:
                                        match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                                        if match:
                                            elem_id = match.group(1)
                                            if elem_id not in child_metric_ids:
                                                child_metric_ids.append(elem_id)
    
    return {
        'tipo': tipo, 
        'formula': formula,
        'function_id': function_id,
        'fact_id': fact_id,
        'child_metric_ids': child_metric_ids  # IDs of child metrics for composite metrics
    }


def extract_expressions_table(soup: BeautifulSoup, object_name: str, anchor: Optional[str] = None) -> List[Dict[str, str]]:
    """Extract EXPRESSÕES table: expression names and source tables."""
    section = find_object_section(soup, object_name, anchor)
    if not section:
        return []
    
    expressions = []
    
    # Find EXPRESSÕES section
    for header in section.find_all('td', class_='SECTIONHEADER'):
        if 'EXPRESSÕES' in header.get_text() or 'EXPRESS' in header.get_text():
            next_table = header.find_next('table')
            if next_table:
                # Find header row to identify columns
                header_row = next_table.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['td', 'th'])]
                    expr_col = None
                    table_col = None
                    
                    for i, h in enumerate(headers):
                        if 'EXPRESSÃO' in h.upper() or 'EXPRESSION' in h.upper():
                            expr_col = i
                        if 'TABELAS FONTE' in h.upper() or 'SOURCE' in h.upper() or 'TABELA' in h.upper():
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


def extract_fact_logic_tables(soup: BeautifulSoup, fact_name: str, anchor: Optional[str] = None) -> List[Dict[str, str]]:
    """Extract logic_tables from Fact EXPRESSÕES section.
    
    Returns a list of logic_table dicts, where each dict contains:
    - name: Table name (e.g., "FT_BARE_RESULT_COML")
    - id: Table ID extracted from HREF [$$$$ID$$$$] format
    - file_path: Optional file path if available from HREF
    - column_name: Column name from EXPRESSÃO field (first column)
    """
    logic_tables = []
    
    # Find anchor if provided
    anchor_tag = None
    anchor_index = None
    if anchor:
        anchor_tag = soup.find('a', {'name': anchor})
        if not anchor_tag:
            # If anchor not found, cannot extract logic tables
            return []
        
        # Get all elements in document order to find anchor position
        all_elements = list(soup.descendants)
        try:
            anchor_index = all_elements.index(anchor_tag)
        except ValueError:
            return []
    
    # Strategy: Navigate from the anchor and find the EXPRESSÕES section
    # The EXPRESSÕES section should be within the same object structure as the anchor
    
    # Use a simpler approach: start from anchor and look for EXPRESSÕES in the next elements
    section_table = None
    current = anchor_tag.find_next('table', class_='SECTIONHEADER')
    
    # Search for EXPRESSÕES section (try up to 20 SECTIONHEADER tables)
    attempts = 0
    max_attempts = 20
    
    while current and attempts < max_attempts:
        header_text = current.get_text(strip=True).upper()
        
        # Check if this is the EXPRESSÕES section
        if 'EXPRESSÕES' in header_text or 'EXPRESS' in header_text:
            section_table = current
            break
        
        # Move to next SECTIONHEADER table
        current = current.find_next('table', class_='SECTIONHEADER')
        attempts += 1
    
    if not section_table:
        # EXPRESSÕES section not found
        return []
    
    # Found EXPRESSÕES section - now find the data table after it
    # The structure is:
    # 1. SECTIONHEADER table with "EXPRESSÕES"
    # 2. Possibly empty table(s)
    # 3. Data table with columns: EXPRESSÃO, MÉTODO DE MAPEAMENTO, TABELAS FONTE
    
    data_table = None
    current = section_table.find_next('table')
    
    # Search for the data table - skip empty tables
    while current:
        # Check if this is the data table by looking at the header row
        rows = current.find_all('tr')
        if rows:
            # Check first row for column headers
            header_row = rows[0]
            header_cells = header_row.find_all(['td', 'th'])
            header_texts = [cell.get_text(strip=True).upper() for cell in header_cells]
            
            # Look for the required columns
            # Handle encoding issues by normalizing text
            # Check for EXPRESSÃO/EXPRESSION column (more flexible matching)
            has_expressao = False
            for h in header_texts:
                h_upper = h.upper()
                h_normalized = normalize_for_comparison(h)
                # Check if it contains "EXPRESS" (handles encoding issues)
                if ('EXPRESS' in h_upper or 'EXPRESS' in h_normalized or
                    h_normalized.startswith('EXPRESS') or h_upper.startswith('EXPRESS')):
                    has_expressao = True
                    break
            
            # Check for TABELAS FONTE column
            has_tabela_fonte = False
            for h in header_texts:
                h_upper = h.upper()
                h_normalized = normalize_for_comparison(h)
                # Check if it contains "TABELAS FONTE" or both "TABELA" and "FONTE"
                if ('TABELAS FONTE' in h_upper or 'TABELAS FONTE' in h_normalized or
                    ('TABELA' in h_upper and 'FONTE' in h_upper) or
                    ('TABELA' in h_normalized and 'FONTE' in h_normalized)):
                    has_tabela_fonte = True
                    break
            
            if has_expressao and has_tabela_fonte:
                # This is the data table we want
                data_table = current
                break
        
        # Move to next table
        current = current.find_next('table')
        
        # Stop if we hit another SECTIONHEADER (we've gone too far)
        if current:
            current_classes = current.get('class', [])
            if isinstance(current_classes, list):
                if 'SECTIONHEADER' in current_classes:
                    break
            elif isinstance(current_classes, str):
                if 'SECTIONHEADER' in current_classes:
                    break
    
    if not data_table:
        return []
    
    # Extract column index for TABELAS FONTE
    header_row = data_table.find('tr')
    if not header_row:
        return []
    
    headers = [th.get_text(strip=True) for th in header_row.find_all(['td', 'th'])]
    expressao_col = None
    table_col = None
    
    # Find the EXPRESSÃO and TABELAS FONTE columns
    # Handle encoding issues by normalizing text
    for i, h in enumerate(headers):
        h_upper = h.upper()
        h_normalized = normalize_for_comparison(h)
        
        # Check for EXPRESSÃO column (first column)
        if ('EXPRESS' in h_upper or 'EXPRESS' in h_normalized or
            h_normalized.startswith('EXPRESS') or h_upper.startswith('EXPRESS')):
            expressao_col = i
        
        # Check for TABELAS FONTE column (third column)
        if ('TABELAS FONTE' in h_upper or ('TABELA' in h_upper and 'FONTE' in h_upper) or
            'TABELAS FONTE' in h_normalized or ('TABELA' in h_normalized and 'FONTE' in h_normalized)):
            table_col = i
    
    if table_col is None:
        return []
    
    # Extract data rows (skip header row)
    for row in data_table.find_all('tr')[1:]:
        cells = row.find_all(['td', 'th'])
        if len(cells) <= table_col:
            continue
        
        # Extract column name from EXPRESSÃO column (first column)
        column_name = None
        if expressao_col is not None and len(cells) > expressao_col:
            column_name = cells[expressao_col].get_text(strip=True)
        
        # Extract logic_tables from the TABELAS FONTE cell (third column)
        table_cell = cells[table_col]
        
        # Find all links in this cell (there may be multiple tables)
        for link in table_cell.find_all('a'):
            table_name = link.get_text(strip=True)
            href = link.get('href', '')
            
            if table_name and href:
                # Extract ID from HREF [$$$$ID$$$$] format
                match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                if match:
                    table_id = match.group(1)
                    
                    # Note: file_path will be resolved later using TabelaLógica.html
                    # For now, we just mark it as None to be filled later
                    
                    # Check if we already have this logic_table (avoid duplicates)
                    if not any(lt['id'] == table_id for lt in logic_tables):
                        logic_tables.append({
                            'name': table_name,
                            'id': table_id,
                            'file_path': None,  # Will be resolved from TabelaLógica.html
                            'column_name': column_name
                        })
    
    return logic_tables


def extract_attribute_forms(soup: BeautifulSoup, object_name: str, anchor: Optional[str] = None) -> List[Dict[str, any]]:
    """Extract DETALHES DOS FORMULÁRIOS DE ATRIBUTO table.
    
    Returns a list of forms, where each form contains:
    - name: Form name (e.g., "ID", "Codigo Agência")
    - logic_tables: List of LogicTable objects with name, id, and column_name
    """
    import re
    
    # Find anchor if provided
    anchor_tag = None
    if anchor:
        anchor_tag = soup.find('a', {'name': anchor})
        if not anchor_tag:
            return []
    
    forms = []
    
    # Strategy: Find DETALHES DOS FORMULÁRIOS section, then process all form anchors
    # that are between this attribute's anchor and the next attribute's anchor
    
    # Find all attribute anchors (32 hex chars, no underscore)
    all_attr_anchors = []
    for a in soup.find_all('a', {'name': True}):
        name = a.get('name', '')
        if len(name) == 32 and '_' not in name and re.match(r'^[A-F0-9]{32}$', name):
            all_attr_anchors.append(a)
    
    # Find current and next attribute anchor indices
    current_idx = None
    next_anchor = None
    if anchor_tag:
        try:
            current_idx = all_attr_anchors.index(anchor_tag)
            if current_idx + 1 < len(all_attr_anchors):
                next_anchor = all_attr_anchors[current_idx + 1]
        except ValueError:
            pass
    
    # Find DETALHES DOS FORMULÁRIOS section after anchor
    section_table = None
    if anchor_tag:
        current = anchor_tag.find_next('table', class_='SECTIONHEADER')
        attempts = 0
        max_attempts = 20
        
        while current and attempts < max_attempts:
            # Stop if we hit next attribute
            if next_anchor:
                # Check if current is after next_anchor
                try:
                    if list(soup.descendants).index(current) >= list(soup.descendants).index(next_anchor):
                        break
                except ValueError:
                    pass
            
            header_text = current.get_text(strip=True).upper()
            if 'DETALHES' in header_text and ('FORMULÁRIO' in header_text or 'FORMULARIO' in header_text):
                section_table = current
                break
            current = current.find_next('table', class_='SECTIONHEADER')
            attempts += 1
    
    if not section_table:
        return []
    
    # Find all form anchors (have underscore) after section_table and before next_anchor
    form_anchors_to_process = []
    current = section_table.find_next('a')
    while current:
        # Stop if we hit next attribute
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
        
        # Get form name from table after anchor
        form_name_table = form_anchor.find_next('table')
        if not form_name_table:
            continue
        
        # Extract form name (it's in bold <B> tag or as text)
        form_name = None
        form_name_rows = form_name_table.find_all('tr')
        if form_name_rows:
            form_name_cell = form_name_rows[0].find('td')
            if form_name_cell:
                # Try to get from <B> tag first
                bold_tag = form_name_cell.find('b')
                if bold_tag:
                    form_name = bold_tag.get_text(strip=True)
                else:
                    form_name = form_name_cell.get_text(strip=True)
        
        if not form_name:
            continue
        
        # Find PROPRIEDADE/VALORES table
        prop_table = form_name_table.find_next('table')
        if not prop_table:
            continue
        
        # Find the nested table inside VALORES cell
        # Look for table with EXPRESSÃO header
        nested_table = None
        for cell in prop_table.find_all('td'):
            # Check if this cell contains a nested table with EXPRESSÃO header
            nested = cell.find('table')
            if nested:
                nested_rows = nested.find_all('tr')
                if nested_rows:
                    nested_headers = [th.get_text(strip=True) for th in nested_rows[0].find_all(['td', 'th'])]
                    if 'EXPRESSÃO' in ' '.join(nested_headers).upper() or 'EXPRESSION' in ' '.join(nested_headers).upper():
                        nested_table = nested
                        break
        
        if nested_table:
            # Found the data table - extract form data
            current_form = {
                'name': form_name,
                'logic_tables': []
            }
            forms.append(current_form)
            
            # Extract data from nested table
            # Each row has: EXPRESSÃO (column_name), MÉTODO DE MAPEAMENTO, TABELAS FONTE
            nested_rows = nested_table.find_all('tr')
            if nested_rows:
                # Find columns
                header_row = nested_rows[0]
                headers = [th.get_text(strip=True) for th in header_row.find_all(['td', 'th'])]
                expr_col = None
                table_col = None
                
                # Handle encoding issues
                for i, h in enumerate(headers):
                    h_upper = h.upper()
                    h_normalized = normalize_for_comparison(h)
                    if ('EXPRESS' in h_upper or 'EXPRESS' in h_normalized or
                        h_normalized.startswith('EXPRESS') or h_upper.startswith('EXPRESS')):
                        expr_col = i
                    if ('TABELAS FONTE' in h_upper or ('TABELA' in h_upper and 'FONTE' in h_upper) or
                        'TABELAS FONTE' in h_normalized or ('TABELA' in h_normalized and 'FONTE' in h_normalized)):
                        table_col = i
                
                # Extract data rows - each row may have multiple tables for the same column
                for row in nested_rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    
                    # Extract column name from EXPRESSÃO column
                    column_name = None
                    if expr_col is not None and len(cells) > expr_col:
                        column_name = cells[expr_col].get_text(strip=True)
                    
                    # Extract source tables - associate each with the column_name
                    if table_col is not None and len(cells) > table_col:
                        table_cell = cells[table_col]
                        for link in table_cell.find_all('a'):
                            table_name = link.get_text(strip=True)
                            href = link.get('href', '')
                            if table_name and href:
                                # Extract ID from HREF [$$$$ID$$$$]
                                match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                                if match:
                                    table_id = match.group(1)
                                    
                                    # Add logic_table with column_name
                                    # Note: file_path will be resolved later from TabelaLógica.html
                                    current_form['logic_tables'].append({
                                        'name': table_name,
                                        'id': table_id,
                                        'file_path': None,  # Will be resolved from TabelaLógica.html
                                        'column_name': column_name
                                    })
    
    return forms


def find_logical_table_link(tabela_logica_index_path: Path, table_name: Optional[str] = None, table_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Find a logical table link in TabelaLógica.html index.
    
    Args:
        tabela_logica_index_path: Path to TabelaLógica.html
        table_name: Optional name of the table
        table_id: Optional ID from HREF [$$$$ID$$$$] format for exact matching
    
    Returns:
        Dict with name, file, anchor, href, and id, or None if not found
    """
    if not tabela_logica_index_path.exists():
        return None
    
    soup = parse_html_file(tabela_logica_index_path)
    
    # First, try to find by ID if provided (most accurate)
    if table_id:
        for link in soup.find_all('a', class_='MAINBODY'):
            href = link.get('href', '')
            # Check if anchor matches the ID
            parts = href.split('#')
            anchor = parts[1] if len(parts) > 1 else ''
            # Also check if ID is in the HREF placeholder format
            if '[$$$$' in href:
                match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                if match and match.group(1).upper() == table_id.upper():
                    return {
                        'name': link.get_text(strip=True),
                        'file': parts[0] if parts else '',
                        'anchor': anchor,
                        'href': href,
                        'id': match.group(1)
                    }
            elif anchor.upper() == table_id.upper():
                return {
                    'name': link.get_text(strip=True),
                    'file': parts[0] if parts else '',
                    'anchor': anchor,
                    'href': href,
                    'id': anchor
                }
    
    # Fallback: search by name
    if table_name:
        for link in soup.find_all('a', class_='MAINBODY'):
            link_text = link.get_text(strip=True)
            if link_text == table_name or table_name in link_text or link_text in table_name:
                href = link.get('href', '')
                parts = href.split('#')
                # Extract ID from HREF if available
                table_id_from_href = None
                if '[$$$$' in href:
                    match = re.search(r'\[\$\$\$\$([A-F0-9]+)\$\$\$\$\]', href)
                    if match:
                        table_id_from_href = match.group(1)
                return {
                    'name': link_text,
                    'file': parts[0] if parts else '',
                    'anchor': parts[1] if len(parts) > 1 else '',
                    'href': href,
                    'id': table_id_from_href or parts[1] if len(parts) > 1 else None
                }
    
    return None

